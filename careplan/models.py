from django.db import models

"""
Patient字段:
id(id 是 Django 自动帮加的字段，不用特地写出来。)
first_name; last_name; mrn(唯一); dob; created_at
"""
class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=6, unique=True)
    dob = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mrn})"

"""
Provider字段:
id(id 是 Django 自动帮加的字段，不用特地写出来。)
name; npi(唯一); created_at
"""
class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.npi})"

"""
CarePlan字段:
id(id 是 Django 自动帮加的字段，不用特地写出来。)
patient (外键 → 指向 Patient.id)
provider (外键 → 指向 Provider.id)
primary_diagnosis; medication_name; medication_history; patient_records; status
generated_content; error_message; created_at; updated_at
"""
class CarePlan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    primary_diagnosis = models.CharField(max_length=50)
    additional_diagnosis = models.TextField(blank=True)
    medication_name = models.CharField(max_length=200)
    medication_history = models.TextField(blank=True)
    patient_records = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_content = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CarePlan for {self.patient} - {self.medication_name} ({self.status})"
