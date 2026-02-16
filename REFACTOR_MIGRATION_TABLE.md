# views.py 拆分迁移表

| 原 views.py 位置 | 迁移目标 | 说明 |
|-----------------|----------|------|
| `json.loads(request.body)` | serializers.py `parse_generate_careplan_request(body)` | 解析 POST JSON → dict |
| Patient/Provider get_or_create、CarePlan create、task.delay | services.py `create_careplan(data)` | 业务逻辑：建 patient/provider/careplan，投递 Celery |
| generate_careplan 的 return JsonResponse | views.py 调用 `services.create_careplan` 后 JsonResponse | view 只负责返回 |
| get_careplan: CarePlan.objects.get、status 判断、构建 response dict | services.py `get_careplan_detail(careplan_id)` | 业务逻辑：查 DB、构建返回 dict |
| get_careplan 的 return JsonResponse | views.py 根据 service 返回值 JsonResponse | view 只负责返回 |
| careplan_status: CarePlan.objects.get、构建 status dict | services.py `get_careplan_status(careplan_id)` | 业务逻辑：查 DB、构建 status dict |
| careplan_status 的 return JsonResponse | views.py 根据 service 返回值 JsonResponse | view 只负责返回 |
| download_careplan: CarePlan.objects.get、status 检查、filename、HttpResponse | services.py `get_careplan_download(careplan_id)` | 业务逻辑：查 DB、返回 (content, filename) |
| download_careplan 的 return HttpResponse | views.py 根据 service 返回值构建 HttpResponse | view 只负责返回 |
| search_careplans: queryset 构建、filter、Q 条件 | services.py `search_careplans(q, export)` | 业务逻辑：查 DB、构建 queryset |
| search_careplans: CSV writer、writerow | services.py `search_careplans(..., export=True)` | 业务逻辑：生成 CSV HttpResponse |
| search_careplans: items 列表构建 | services.py `search_careplans(..., export=False)` | 业务逻辑：构建 results 列表 |
| search_careplans: 取 q、export | views.py 从 request.GET 取参数并传给 service | view 只负责取参、调用、返回 |
| search_careplans 的 return | views.py 根据 export 返回 JsonResponse 或 HttpResponse | view 只负责返回 |
