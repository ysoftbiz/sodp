from django.contrib.auth import dashboard, createReport
from django.shortcuts import redirect

def createReportView(request):
    createReport(request)
    return redirect('homepage')