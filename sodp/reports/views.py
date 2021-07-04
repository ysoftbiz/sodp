from django.shortcuts import render
from django.http import HttpRequest
from models import report

class reportsView(HttpRequest):
    def list_reports(request):
        reports = report.objects.all()
        return render(request,"dashboard.html",{"reports":requests})