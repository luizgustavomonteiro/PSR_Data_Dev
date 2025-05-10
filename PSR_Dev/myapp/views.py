from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'home.html', {})

def maps(request):
    return render(request, 'maps.html', {})

def graphs(request):
    return render(request, 'graphics.html', {})

def team(request):
    return render(request, 'developmentTeam.html', {})