from django.contrib import admin
from .models import Patient, Provider, CarePlan

admin.site.register(Patient)
admin.site.register(Provider)
admin.site.register(CarePlan)
