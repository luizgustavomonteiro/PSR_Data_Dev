from django.db import models

# Create your models here.

'''
- Models to store the datadownloads from TABNET DATASUS
- This data will be download using Selenium library to map the empidemiological disease webpage
- A model is the single, definitive source of information about your data. It contains the essential fields and behaviors of the data you’re storing. 
Generally, each model maps to a single database table.
'''

# Classes for each table at database

# Diseases Model
class Diseases(models.Model):
    disease_id = models.AutoField(primary_key=True) # Automatically increment unique ID
    disease_name = models.CharField(max_length=60, unique=True) # Unique name of Disease

# Regions Model
class Regions(models.Model):
    region_id = models.AutoField(primary_key=True) # Automatically increment unique ID
    region_name = models.CharField(max_length=3, unique=True) # Unique region name (e.g. SP)

# Notifications Model

class Notifications(models.Model):
    notification_id = models.AutoField(primary_key=True) # Automatically increment unique ID
    disease = models.ForeignKey(Diseases, on_delete=models.CASCADE) # ForeignKey with Diseases Table, if some deleted disease, the programm will delete all relationships
    region = models.ForeignKey(Regions, on_delete=models.CASCADE)
    notification_week = models.IntegerField()
    notification_year = models.IntegerField()
    cases_confirmed = models.IntegerField()
    deaths_confirmed = models.IntegerField()

    def __str__(self):
        return f"Notification for {self.disease} in {self.region} for Week {self.notification_week}, Year {self.notification_year}"
    
    '''Define the text representation of notification.
        When a object will be print:
"Notification for Dengue in SP for Week 12, Year 2025".'''