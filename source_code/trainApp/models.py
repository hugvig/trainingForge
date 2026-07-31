from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


"""
This is the base class for any user. 
It makes it simpler to manage the authentication of each user
It sets all the common fields for athletes and coaches.
It sets the REQUIRED_FIELD (fields that are required to create a new user).
We will be using the Role class to differentiate the type of user. Either Athlete or Coach (a corresponding profile will be created).
"""
class User(AbstractUser):
    #Setting the choices for the role of the user.
    class Role(models.TextChoices):
        Athlete = "Athlete", "Athlete"
        Coach = "Coach", "Coach"

    #The email field will have to be unique to each user.
    email = models.EmailField(unique=True)

    #The role of the user. The choices are set in the Role class.
    role = models.CharField(max_length=7, choices=Role.choices)

    #If the user is active
    is_active = models.BooleanField(default=True)

    #If the user is admin
    is_admin = models.BooleanField(default=False)

    #We setting all the required fields to create a new user. USERNAME_FIELD is also included.
    #REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


"""
This is the Athlete profile. It is going to be used while creating a user to make it an athlete.
It inherits the User class so it gets all of its fields.
It will contain all the information specific to an athelte.
"""
class AthleteProfile(models.Model):
    #The choices for the level of an athlete. format (python accessible = DATA_BASE_VIEW, USER_VIEW)
    class Level(models.TextChoices):
        BE = "BEGINNER", "Beginner"
        IN = "INTERMEDIATE", "Intermediate"
        AD = "ADVANCED", "Advanced"
        PR = "PRO", "Pro"

    #The link to the user. If the user is deleted this object will also be deleted.
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    #The level of the athlete.
    level = models.CharField(max_length=12, choices=Level.choices)

    #The weight of the athlete.
    weigth = models.PositiveSmallIntegerField()

    #If there are more information to store about the athlete.
    about = models.TextField("Athlete info", blank=True, default="", help_text="More about the athlete.")

    def __str__(self):
        return self.user.username


"""
This is the Coach profile. It is going to be used while creating a user to make it a coach
It inherits the User class so it gets all of its fields
It will contain all the information specific to a Coach
"""
class CoachProfile(models.Model):
    #The choices for the role of the coach. format (python_accessible = DATA_BASE_VIEW, USER_VIEW)
    class Role(models.TextChoices):
        CC = "CONDITIONNING_COACH", "Conditionning coach"
        WC = "WEIGHTLIFTING_COACH", "Weightlifting coach"

    #The link to the user. If the user is deleted this object will also be deleted.
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    #The role of the coach.
    role = models.CharField(max_length=50, choices=Role.choices)

    def __str__(self):
        return self.user.username


"""
This is the class for the training groups. Each training group will have a coach and many athletes.
"""
class Training_Group(models.Model):
    #The name of the group (required).
    name = models.CharField(max_length=50, unique=True, blank=False)

    #The specific sport of the athletes in this group (optional).
    sport = models.CharField(max_length=50)

    #The athletes of this group
    athletes = models.ForeignKey(AthleteProfile, on_delete=models.PROTECT)

    #The coach of this group
    coach = models.OneToOneField(CoachProfile, on_delete=models.PROTECT)


"""
This is the Training program class. 
It will store information related to programs.
"""
class Programs(models.Model):
    #The name of the program.
    name = models.CharField(max_length=50, unique=True)
   

"""
This is the exercice class. 
It will hold all the information about an exercice.
"""
class Exercice(models.Model):
    #The style of exercice (weightlifting, cardio, muscu, etc)
    class Exercice_style(models.TextChoices):
        ONE = "1", "1"
        TWO = "2", "2"
        THREE = "3", "3"

    #The name of the exercice
    name = models.CharField(max_length=50, unique=True)

    #The style of the exercice
    style = models.CharField(max_length=50, choices=Exercice_style.choices)

    #The targeted muscles
    targeted_muscles = models.TextField("Targeted muscles", blank=False, help_text="The muslces targeted by the excercice")

    #The general description for the exercice
    description = models.TextField("Info", blank=True, help_text="Describe how the excercice should be done (optional)")

    #The link to a (one or more) training programs
    programs = models.ManyToManyField(Programs, related_name='exercice')
