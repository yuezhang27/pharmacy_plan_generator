from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import csv
import json
from datetime import datetime
from .models import Patient, Provider, CarePlan
from .llm_service import generate_careplan_with_llm

# Django框架下，加载主页面
# 和urls.py里path('', views.index, name='index') 连起来看，就是
# 当访问路径是根路径('')的时候，调用index方法，render的就是index.html（这是个template，内容会被渲染到template里）
def index(request):
    return render(request, 'careplan/index.html')

"""
处理request以生成careplan，包括对应patient，provider，careplan的实例化，以及数据库的更新
"""
# csrf_exempt：用来关闭某个view的CSRF校验
@csrf_exempt
def generate_careplan(request):
    # 既然是点击按钮生成careplan，肯定得是POST请求，不过这个更多是在error handling，加不加其实都行
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # 首先从请求体里，加载post过来的数据
        data = json.loads(request.body)
        
        # Get or create patient
        # 这个是Django带来的"get_or_create"方法，好处是，对于某一些object，有就查找并返回，没有就新建object
        # 前面要两个变量，是因为get_or_create会返回一个object和一个bool，代表是否查找到，这里业务上暂时没啥意义，所以_来存这个就行
        # 从data里的信息，加载（新建/获取）出这个patient
        patient, _ = Patient.objects.get_or_create(
            mrn=data['patient_mrn'],
            defaults={
                'first_name': data['patient_first_name'],
                'last_name': data['patient_last_name'],
                'dob': datetime.strptime(data['patient_dob'], '%Y-%m-%d').date()
            }
        )

        # Get or create provider
        # 同上，从data里拆出信息，新建/获取provider对象
        provider, _ = Provider.objects.get_or_create(
            npi=data['provider_npi'],
            defaults={'name': data['provider_name']}
        )

        # Create care plan with pending status
        # 这里目前的处理是，在初始化careplan对象的时候，status先默认设置成pending
        careplan = CarePlan.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis=data['primary_diagnosis'],
            additional_diagnosis=data.get('additional_diagnosis', ''),
            medication_name=data['medication_name'],
            medication_history=data.get('medication_history', ''),
            patient_records=data['patient_records'],
            status='pending'
        )

        # Update to processing
        # 刚才初始化完成了careplan，所以这里把status改成processing
        careplan.status = 'processing'
        # model.save() 就是把 当前CarePlan实例同步到数据库：insert或者update。这里是对应insert
        careplan.save()

        # Generate care plan with LLM
        # 前面已经生成careplan的实例，这里就可以调用generate_careplan_with_llm
        # 生成careplan，把llm生成的careplan，存到generated_content这个变量
        try:
            generated_content = generate_careplan_with_llm(
                patient=patient,
                provider=provider,
                primary_diagnosis=careplan.primary_diagnosis,
                additional_diagnosis=careplan.additional_diagnosis,
                medication_name=careplan.medication_name,
                medication_history=careplan.medication_history,
                patient_records=careplan.patient_records
            )
            
            # 已经生成careplan了，所以改status为completed
            careplan.status = 'completed'
            # 把这个生成的careplan的内容（llm返回的内容）传递给careplan变量
            careplan.generated_content = generated_content
            # 更新数据库，这样数据库里就有刚才的plan了
            careplan.save()
            
            # 处理完成，返回response给前端
            return JsonResponse({
                'success': True,
                'careplan_id': careplan.id,
                'status': careplan.status,
                'content': generated_content
            })
        except Exception as e:
            careplan.status = 'failed'
            careplan.error_message = str(e)
            careplan.save()
            
            return JsonResponse({
                'success': False,
                'error': str(e),
                'careplan_id': careplan.id,
                'status': careplan.status
            }, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

"""
使用careplan_id从数据库中获取对应careplan数据，并把数据内容包进json返回
"""
@csrf_exempt
def get_careplan(request, careplan_id):
    try:
        # Django框架下，数据库的读取操作
        # 使用careplan_id从数据库中获取对应careplan数据，存入careplan这个变量里
        careplan = CarePlan.objects.get(id=careplan_id)
        
        # 如果careplan还没有完成，response报错
        if careplan.status != 'completed':
            return JsonResponse({
                'status': careplan.status,
                'error': careplan.error_message if careplan.status == 'failed' else 'Care plan is not ready yet'
            }, status=400)
        
        # 对于完成了的careplan，把数据包入json response并返回
        return JsonResponse({
            'id': careplan.id,
            'status': careplan.status,
            'content': careplan.generated_content,
            'patient': {
                'first_name': careplan.patient.first_name,
                'last_name': careplan.patient.last_name,
                'mrn': careplan.patient.mrn
            },
            'medication': careplan.medication_name,
            'created_at': careplan.created_at.isoformat()
        })
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)

"""
用careplan_id获取careplan，并放入txt文件，放入response返回
"""
def download_careplan(request, careplan_id):
    """
    下载单个 care plan 的文本文件（只在 completed 状态下有内容）。
    不做额外校验或权限控制，最小可用版本。
    """
    # 这部分同get_careplan(request, careplan_id)，都是用careplan的id，读数据库获取careplan
    try:
        careplan = CarePlan.objects.get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return HttpResponse("Care plan not found", status=404)

    if careplan.status != 'completed' or not careplan.generated_content:
        return HttpResponse("Care plan is not completed yet", status=400)

    # 下载的careplan文件的格式 careplan_mrn_medname.txt
    filename = f"careplan_{careplan.patient.mrn}_{careplan.medication_name}.txt"
    # generated_content是之前生成careplan之后存入的careplan内容
    # 把它包进response体里
    response = HttpResponse(careplan.generated_content, content_type='text/plain; charset=utf-8')
    # 在response里加上下载附件
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def search_careplans(request):
    """
    最简单的 search + 导出功能：
    - GET /api/search-careplans/?q=xxx       返回 JSON 列表
    - GET /api/search-careplans/?q=xxx&export=1  返回 CSV 报表
    只搜索已 completed 的 care plan。
    """

    # 取 URL 里的 ?q=xxx的搜索词
    # 其中q=xxx这个是搜索词，是Django的用法
    q = (request.GET.get('q') or '').strip()

    # 构建一个“基础查询条件的 QuerySet”，相当于新建一条还没执行的SQL查询描述
    # 新建queryset，从CarePlan.objects这个对应的表获取，要求：
    # - status为completed，join了patient和provider表一起查，结果按照created_at降序排
    queryset = (
        CarePlan.objects
        .filter(status='completed')
        .select_related('patient', 'provider')
        .order_by('-created_at')
    )

    if q:
        # 在原查询条件（上面的queryset）上再叠加 WHERE条件，继续构造SQL的条件
        # 等价于SQL：
        # WHERE status = 'completed'
        # AND (
        # patient.first_name ILIKE '%q%'
        # OR patient.last_name ILIKE '%q%'
        # OR patient.mrn ILIKE '%q%'
        # )

        queryset = queryset.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__mrn__icontains=q)
            | Q(provider__name__icontains=q)
            | Q(provider__npi__icontains=q)
            | Q(medication_name__icontains=q)
            | Q(primary_diagnosis__icontains=q)
        )
    
    # -------------------------------------------------
    # 到这里，上面是queryset查询语句的构建，注意，这里只是构建语句，没有执行
    # 下面开始，同一个queryset被两个“输出模式”复用：情况1（export=1）导出 CSV；情况2（一定发生）返回 JSON。
    # -------------------------------------------------

    # 情况1，需要export，导出 CSV 报表
    if request.GET.get('export') == '1':
        # 首先构建response体，并且设定好，要加入csv文件
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="careplans_report.csv"'

        # 新建writer用于写入csv，把需要的所有列head都写到csv里
        writer = csv.writer(response)
        writer.writerow([
            'patient_mrn',
            'patient_first_name',
            'patient_last_name',
            'patient_dob',
            'provider_name',
            'provider_npi',
            'medication_name',
            'primary_diagnosis',
            'careplan_created_at',
            'duplication_warning',  # 目前不实现逻辑，先留空
        ])

        # queryset是lazy的！！这里很有趣，上面那些只是构建语句，到for cp in queryset，这里才是真正触发查询
        # 为什么 for cp in queryset 会触发查询？
        # 因为：QuerySet 是 lazy（惰性）；for迭代它时，Python 必须拿到数据，因此这才开始真的查询
        # Django 就在这一步 evaluate queryset → 执行 SQL → 拉数据
        # 同类“触发执行”的操作还有：
        # list(queryset)
        # len(queryset)
        # bool(queryset)
        # queryset[:50]
        
        # 这样，cp就是查询完过滤剩下的数据，一条条写入csv
        for cp in queryset:
            writer.writerow([
                cp.patient.mrn,
                cp.patient.first_name,
                cp.patient.last_name,
                cp.patient.dob.isoformat(),
                cp.provider.name,
                cp.provider.npi,
                cp.medication_name,
                cp.primary_diagnosis,
                cp.created_at.isoformat(),
                '',  # duplication_warning 占位
            ])

        return response

    # 情况2(常规情况)逻辑同上，这里是返回 JSON 用于前端渲染展示
    items = []
    for cp in queryset[:50]:  # 最多返回 50 条，足够 MVP 使用
        items.append({
            'id': cp.id,
            'patient_name': f"{cp.patient.first_name} {cp.patient.last_name}",
            'patient_mrn': cp.patient.mrn,
            'provider_name': cp.provider.name,
            'provider_npi': cp.provider.npi,
            'medication_name': cp.medication_name,
            'primary_diagnosis': cp.primary_diagnosis,
            'created_at': cp.created_at.isoformat(),
            'download_url': f'/download-careplan/{cp.id}/',
        })

    return JsonResponse({'results': items})
