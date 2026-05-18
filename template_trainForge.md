# Base De Donnée
## Utilisateur
- ID
- Nom
- email/numéro de téléphone
- niveau
- Poids/Taille
- objectifs

## entraineurs
- ID 
- Nom
- email/numéro de téléphone
- prep physique/entraineur

## coach_athlete
- ID
- Coach_id
- User_id
- Role (entraineur principale, assistant)
- Date_start

## Exercices
- ID
- nom
- Type (haltéro, assistance, cardio)
- Groupe musculaire
- description
- lien vidéo
### Optionnel
    - Type de technique (Pull, squat, réception)
    - Priorité technique (position, vitesse)

## Programmes
- ID
- Nom du programme 
- Durée 
- Objectif (force, peak, technique)
- Créateur

## Séances
- ID
- Programmes_id
- Jour 1,2..
- Focus (upper, lower, snatch, epj...)
 
## Séries / Performances
- ID
- Workout ID
- Exercices ID
- Sets
- Reps
- Poids (% ou Kg)
- Tempo
- RPE 
- Repos

## workout log
- ID
- Workout_id
- User_id
- Date reelle
- Status (planned, completed, skipped)


## Méthodes d'entrainement
- ID
- Nom
- Description
- Type

## Messages
- ID
- Sender_id
- Receiver_id
- Group_id
- Content
- Timestamp

## Group 
- Entraineur_id
- Nom_entraineur
- Group_id
- Group_nom
- group messaging

# Calendrier
## Intégration de google calendar
- Lier les plans au calendrier
- associer plan a entraineur


# Compression des fichiers de plans antérieur

# HA pour les serveurs
