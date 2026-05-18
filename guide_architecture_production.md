# Guide architecture & production — TrainForge

Pour une équipe de 2 personnes qui démarre, qui auto-héberge à domicile, et qui veut construire quelque chose de sérieux sans se noyer dans la complexité.

**Principe directeur :** ne fais que ce qui est nécessaire **maintenant**, mais ne te bloque pas pour **plus tard**. La complexité prématurée tue les petites équipes. L'absence totale de discipline aussi.

---

## 0. Stack recommandé

Tu m'as dit "ouvert, recommande". Voici mes choix, justifiés.

| Couche | Choix | Pourquoi |
|---|---|---|
| **Backend** | **Python + Django + Django REST Framework** | Domaine riche (athlètes, exos, prescriptions paramétriques, périodisation) → l'ORM Django et son admin auto te font gagner des semaines. DRF expose une API REST propre que ton futur frontend mobile pourra consommer. |
| **Frontend** | **React + TypeScript + Vite + TailwindCSS** | Standard de l'industrie. Compétences transférables à **React Native** le jour où tu fais l'app mobile (50% du code partageable via Expo). |
| **BDD** | **PostgreSQL 16** | Le seul choix raisonnable. JSONB pour les prescriptions paramétrées, Row-Level Security pour le multi-tenant, fiabilité prouvée. |
| **Cache / Queue** | **Redis** *(plus tard)* | Sessions, rate-limiting, cache des 1RM, et plus tard files d'attente pour Celery. |
| **Background jobs** | **Celery + Redis** *(plus tard)* | Calculs lourds (suggestions de progression, recomputes de stats) hors du cycle HTTP. |
| **Reverse proxy / HTTPS** | **Caddy** | Configure HTTPS automatiquement via Let's Encrypt en 3 lignes. nginx est puissant mais Caddy te suffit largement et te fait gagner du temps. |
| **Conteneurisation** | **Docker + docker-compose** | Une image backend, une image frontend, postgres, redis, caddy. Même fichier en dev et en prod (paramétré par env vars). |

**Alternative considérée :** TypeScript full-stack (Next.js + NestJS). Bonne stack moderne mais Django est plus rapide à scaffolder pour un domaine riche comme le tien, et tu auras moins de boilerplate côté permissions/admin/migrations.

**Ce que tu n'utilises PAS au démarrage :** Kubernetes, GraphQL, microservices, serverless, gRPC, monorepo Nx/Turborepo, message broker dédié (Kafka/RabbitMQ). Tu pourrais — mais ça ne sert que quand tu as un vrai problème à résoudre, pas avant.

---

## 1. Architecture

### Monolithe modulaire, point final.

À ton stade, microservices = suicide d'équipe. Tu ajoutes 10× la complexité opérationnelle (réseau interservices, déploiements coordonnés, observabilité distribuée, débogage cauchemardesque) pour zéro bénéfice business.

Ce qui marche : un **monolithe bien découpé en modules** (bounded contexts) à l'intérieur. Le jour où un module devient un goulot d'étranglement, tu l'extrais — pas avant.

### Structure backend (Django apps par bounded context)

```
trainforge/
├── apps/
│   ├── identity/        # users, auth, organisations, roles
│   ├── athletes/        # profil athlète, 1RM, anthropométrie
│   ├── exercises/       # bibliothèque d'exercices, catégories
│   ├── programs/        # phases, semaines, séances, prescriptions
│   ├── progression/     # logique de progression, suggestions
│   └── reporting/       # vues d'ensemble, analytics
├── config/              # settings, urls, asgi/wsgi
├── core/                # utilitaires partagés, classes de base
└── manage.py
```

Chaque app a son `models.py`, ses `views.py` (DRF viewsets), ses `serializers.py`, ses tests. Les dépendances entre apps doivent aller dans **un seul sens** (identity ne dépend de personne ; programs dépend de athletes et exercises ; jamais l'inverse).

### Structure frontend

```
src/
├── api/                 # clients HTTP générés ou à la main
├── features/            # un dossier par feature (athletes, programs, ...)
│   └── athletes/
│       ├── components/
│       ├── hooks/
│       └── routes.tsx
├── shared/              # design system, composants UI réutilisés
├── lib/                 # auth, fetch wrapper, query client
└── app.tsx
```

Utilise **TanStack Query** (anciennement React Query) pour tout l'état serveur. Tu n'auras pas besoin de Redux.

### Load balancing — quand ?

**Pas maintenant.** Tu ne load-balances pas avant d'avoir un problème de charge. Un serveur Django bien configuré (Gunicorn 4-8 workers, derrière Caddy) tient confortablement plusieurs milliers d'utilisateurs actifs si la DB suit.

Quand l'introduire : quand tu vois ton CPU plafonner > 70% en continu, ou quand tu veux du zero-downtime deploy. Tu mets alors **2 instances backend** derrière Caddy (Caddy fait le load balancing nativement), avec **sessions stockées en Redis** (pas en mémoire — voir section Scalabilité).

---

## 2. Sécurité — la priorité

C'est la section la plus importante. Une fuite de données sur des athlètes (poids, santé, performances) = fin du projet. Pas de seconde chance.

### Maintenant — non négociable

- **HTTPS partout.** Caddy + Let's Encrypt, ça prend 5 minutes. Aucun trafic en clair, jamais. HSTS activé.
- **Hash des mots de passe avec Argon2id.** Django supporte Argon2 nativement (`django[argon2]`). N'utilise pas MD5, SHA1, ni bcrypt si tu peux faire mieux.
- **Authentification : sessions httpOnly + Secure cookies** pour le web (plus simple, plus sûr que JWT pour ton cas). Switch vers JWT/refresh tokens **uniquement** quand tu introduiras l'app mobile.
- **CSRF activé** côté Django (par défaut). N'expose pas d'endpoints qui modifient l'état sans CSRF token.
- **CORS strict.** N'autorise que ton propre domaine frontend.
- **Validation systématique côté serveur** (DRF serializers). Ne fais JAMAIS confiance au frontend.
- **Variables sensibles dans `.env`**, jamais dans le code, jamais dans git. Utilise `django-environ` ou `pydantic-settings`.
- **Rate limiting** sur les endpoints d'auth (`django-ratelimit` ou `django-axes`) — 5 tentatives de login par minute par IP.
- **Headers de sécurité** : `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. Caddy peut les injecter.
- **Logs d'audit** sur les actions sensibles (login, changement de password, accès admin, suppression d'athlète).

### Erreurs critiques à éviter absolument

1. **Stocker des mots de passe en clair ou avec MD5/SHA1.** Disqualifiant.
2. **Endpoints de modification sans authentification ni autorisation.** Vérifie *à chaque endpoint* que l'utilisateur a le droit de toucher *à cette ressource précise* (pas juste qu'il est connecté). C'est le fameux IDOR (Insecure Direct Object Reference). Sur ton domaine multi-tenant, c'est la faille n°1.
3. **Secrets en clair dans le repo Git** (clés API, mots de passe DB, `SECRET_KEY` Django). Si c'est arrivé une fois, **rotate** tout immédiatement — git rewrite ne suffit pas.
4. **`DEBUG=True` en production.** Django affiche alors les stack traces complètes aux visiteurs. Combine avec une SQL injection et c'est game over.
5. **Pas de backups, ou backups jamais testés.** Voir section BDD.
6. **Pas de mise à jour de sécurité.** Active `dependabot` (GitHub) ou `renovate` pour suivre les CVE de tes dépendances.
7. **Mass-assignment.** Avec DRF, déclare explicitement les `fields` dans tes serializers (jamais `fields = '__all__'` pour des modèles qui ont des champs sensibles comme `is_staff`, `is_superuser`, `tenant_id`).
8. **Stocker la santé/identité des athlètes sans réflexion RGPD.** Si tu vises des coachs européens, tu es soumis au RGPD. Données minimales, consentement, droit à l'effacement, registre des traitements.

### Protection des données utilisateurs

- **Chiffrement en transit :** TLS (HTTPS).
- **Chiffrement au repos :** chiffre le disque du serveur (LUKS sur Linux). Quand tu enverras des backups off-site, chiffre-les avec `age` ou GPG avant l'upload.
- **Minimisation des données.** Ne stocke pas ce dont tu n'as pas besoin. Pas de date de naissance si seul l'âge suffit. Pas de numéro de téléphone si l'email suffit.
- **Mentions légales + politique de confidentialité** dès le premier utilisateur externe, même beta.

---

## 3. Scalabilité — concevoir pour scaler, pas scaler tout de suite

L'objectif à ton stade n'est **pas** de supporter 1M d'utilisateurs. C'est de **ne pas peindre l'app dans un coin** dont tu ne pourras pas sortir.

### Choix structurels qui te préservent l'avenir

- **Application stateless.** Ne stocke **jamais** d'état utilisateur dans la mémoire d'un process Python. Sessions → Redis. Uploads → stockage objet (MinIO en local, S3/Backblaze B2 plus tard). Cache → Redis. Tout doit pouvoir être tué et redémarré sans perdre d'état.
- **DB = ressource unique partagée.** C'est la pièce qui va te limiter en premier. Tout le reste se duplique facilement.
- **API versionnée dès le départ :** `/api/v1/...`. Le jour où tu fais l'app mobile, tu pourras faire `/api/v2/` sans casser le web.
- **Pagination obligatoire sur toutes les listes.** Jamais de `Athlete.objects.all()` retourné brut dans une vue. DRF a `PageNumberPagination` ou `CursorPagination` (préfère le cursor pour les grosses listes).
- **N+1 queries = ennemi public n°1.** Utilise `select_related` / `prefetch_related` systématiquement. Installe **`django-debug-toolbar`** en dev pour les voir.
- **Index sur toutes les colonnes filtrantes** (tenant_id, user_id, athlete_id, dates). Django ne crée pas tous les index pour toi.
- **Background jobs pour le lent.** Tout calcul > 200ms (rapports, suggestions de programme, recompute de stats) → Celery. Pas dans le cycle HTTP.

### Quand scaler vraiment

| Symptôme | Action |
|---|---|
| CPU app server > 70% en pointe | Ajoute un second process backend, load balancing via Caddy |
| Latence DB > 100ms sur des queries simples | Profile (`pg_stat_statements`), ajoute des index, pose du cache Redis |
| Connections DB qui saturent | Mets **PgBouncer** devant Postgres |
| Trop d'attente sur jobs lents | Augmente le nombre de workers Celery |

Ne fais **rien** de tout ça avant que le symptôme apparaisse. Mesure d'abord.

---

## 4. Déploiement & DevOps

### Le minimum vital

- **Git** + **GitHub** (ou GitLab) pour le code. Branche `main` protégée, PRs avec review (même si tu reviews seul, ça te force à relire).
- **Docker + docker-compose** pour le dev local *et* la prod. Un seul `docker-compose.yml` avec des overrides (`docker-compose.prod.yml`) pour la prod.
- **CI/CD : GitHub Actions.** Sur chaque push : lint (ruff pour Python, eslint pour TS), tests, build des images Docker, push vers un registry (Docker Hub gratuit, ou GitHub Container Registry).
- **Déploiement :** au début, **un script shell** qui `ssh` sur le serveur, fait `git pull` + `docker-compose pull && docker-compose up -d` suffit. Pas besoin de Kubernetes, Ansible, Terraform.

### Stratégie de déploiement

- **Migrations DB d'abord, code ensuite.** Toujours dans cet ordre. Les migrations doivent être *backwards-compatible* pendant la transition (jamais de DROP COLUMN dans la même release qui en a encore besoin).
- **Déploie souvent, en petites releases.** Plus tu déploies, moins chaque déploiement est risqué.
- **Rollback rapide.** Garde toujours l'image Docker précédente disponible. Un `docker-compose up -d` avec le tag précédent te ramène en arrière en 30 secondes.
- **Plus tard :** zero-downtime via 2 instances + Caddy qui draine. Pour l'instant, une fenêtre de 10s de maintenance est acceptable.

### Monitoring (du jour 1)

- **Sentry** (gratuit jusqu'à 5k events/mois) — capture les exceptions front et back. Indispensable.
- **Uptime Kuma** (self-hosted gratuit) ou **UptimeRobot** — ping ton endpoint `/health` toutes les minutes, alerte par email/Telegram si down.
- **Logs centralisés :** au début, `docker-compose logs -f` et `journalctl` te suffiront. Quand ça grossit : **Grafana Loki** (self-hosted) ou **Better Stack** (SaaS).
- **Métriques applicatives :** plus tard, **Prometheus + Grafana** (self-hosted) pour CPU, mémoire, latence requêtes, taux d'erreur. Pas besoin avant 2-3 mois de prod.

### Endpoint `/health`

Implémente dès le premier déploiement un endpoint qui :
1. Vérifie la connexion DB
2. Vérifie Redis (si présent)
3. Retourne 200 OK avec la version actuelle, 503 sinon

C'est ce que ton monitoring va piquer, et c'est ce qui te permettra de savoir si une release est OK après déploiement.

---

## 5. Base de données

### Structure

- **PostgreSQL.** Pas MySQL, pas SQLite en prod, pas Mongo (tu as des données fortement relationnelles).
- **3NF par défaut**, dénormalise *uniquement* quand tu as un problème de performance mesuré.
- **JSONB pour la flexibilité ciblée** — par exemple le champ `prescription` d'une `SessionExercise` peut être un JSONB `{"sets": 5, "reps": 3, "percent": 85, "rpe": null, "tempo": "30X1"}`. Tu garderas la structure ouverte sans multiplier les colonnes.
- **UUIDs comme primary keys** (pas auto-increment) — masque la volumétrie, évite l'énumération, simplifie la fusion future entre environnements.
- **Soft delete (`deleted_at`)** sur les entités métier (athlètes, programmes). Une suppression définitive perd des données précieuses ; un coach veut souvent voir l'historique d'un ancien athlète.
- **`created_at` / `updated_at`** sur toutes les tables, automatiquement.
- **Migrations versionnées** (Django migrations) — jamais de SQL exécuté à la main en prod.

### Performance

- Index sur toutes les FK et toutes les colonnes filtrantes (`tenant_id`, `athlete_id`, `coach_id`, dates).
- Active `pg_stat_statements` pour identifier les requêtes lentes.
- **EXPLAIN ANALYZE** sur les requêtes critiques.
- Connection pooling via **PgBouncer** quand tu auras plus de ~30 connections simultanées.

### Backups — la partie où on ne plaisante PAS

Avec auto-hébergement à domicile, c'est doublement critique : tu n'as personne d'autre pour t'en occuper.

- **`pg_dump` quotidien**, automatisé par cron. Garde 7 jours sur place + 30 jours off-site + 1 par mois sur l'année.
- **Off-site obligatoire.** Backblaze B2 ou Wasabi (~5€/mois pour ton volume). **Chiffre côté client** avec `age` avant l'upload — la clé ne quitte pas ta machine.
- **WAL archiving** pour le Point-in-Time Recovery quand tu auras une vraie volumétrie. Plus tard.
- **Teste tes restores une fois par mois.** Un backup jamais testé n'existe pas. C'est l'erreur classique : on découvre que les backups sont corrompus le jour où on en a besoin.
- **Documente la procédure de restauration**, étapes claires, dans un fichier `RUNBOOK.md` au repo.

---

## 6. Multi-tenant — comment gérer plusieurs coachs / organisations

### Trois patterns possibles

| Pattern | Coût | Isolation | Quand |
|---|---|---|---|
| **Shared DB, shared schema** (un seul Postgres, une colonne `organization_id` sur chaque table) | Faible | Logique | **Ton choix.** Simple, scalable, le standard B2B SaaS. |
| Shared DB, schema séparé par tenant | Moyen | Schéma | Quand la régulation l'exige (rare pour des coachs sportifs) |
| DB par tenant | Élevé | Physique | Gros clients enterprise avec exigences contractuelles |

**Recommandation : shared DB, shared schema, avec colonne `organization_id` (ou `tenant_id`) sur toutes les tables métier.**

### Implémentation propre

1. **Modèle de base** :
   ```python
   class TenantOwnedModel(models.Model):
       organization = models.ForeignKey('identity.Organization', on_delete=models.CASCADE, db_index=True)
       class Meta:
           abstract = True
   ```
   Tous tes modèles métier héritent de ça.

2. **Filtrage automatique** dans les viewsets DRF — n'utilise *jamais* `Model.objects.all()`, toujours `Model.objects.filter(organization=request.user.organization)`. Encapsule ça dans un mixin pour ne jamais l'oublier.

3. **Row-Level Security PostgreSQL** comme défense en profondeur. Active des policies RLS qui empêchent un user de lire des lignes hors de son organisation, *même si* le code applicatif a un bug. Ceinture + bretelles.

4. **Tests automatisés cross-tenant** : pour chaque endpoint, un test qui vérifie que l'user A ne peut PAS lire/modifier les données de l'user B. À mettre dans la CI dès le début.

### Rôles & permissions

Ton domaine a au moins trois rôles distincts :
- **Coach** (head coach) — voit et modifie ses athlètes, crée des programmes
- **Préparateur physique** — accès partiel selon ce que le coach délègue
- **Athlète** — voit son propre profil et ses programmes

Utilise **`django-guardian`** ou **Casbin** pour des permissions au niveau objet (pas juste "ce user peut modifier *des* athlètes" mais "ce user peut modifier *cet* athlète").

Modèle minimal :
```
Organization
  ├── Memberships (User × Organization × Role)
  └── Athletes
        └── AthleteCoaches (Athlete × User × CoachRole)
```

---

## 7. Sur l'auto-hébergement à domicile — la vérité

Tu m'as dit "serveur perso à la maison". C'est ok pour démarrer, mais il faut nommer les limites par rapport à ton objectif "crédible pour des organisations plus importantes".

### Ce qui passe

- Développement, tests, démos.
- Premiers utilisateurs beta (5-10 coachs proches, qui acceptent que ça soit un peu instable).
- Itérer sans budget infra.

### Ce qui ne passe pas

- **Disponibilité.** Coupure d'électricité, redémarrage box internet, coupure FAI = ton service down. Aucune organisation sérieuse ne signera avec un fournisseur qui dépend du voisinage électrique de sa maison.
- **IP résidentielle.** Souvent dynamique (DDNS aide), parfois en CGNAT (tu n'as littéralement pas d'IP publique routable — vérifie chez ton FAI).
- **Bande passante asymétrique.** Tu as 1 Gbps download mais 50-200 Mbps upload, et c'est l'upload qui compte pour servir des clients.
- **Sécurité physique.** Si quelqu'un entre chez toi, il a accès au serveur. Pour des données d'athlètes pros un jour, c'est un problème.
- **RGPD / responsabilité.** Si tu héberges des données d'athlètes professionnels et que ton serveur est saisi/saisi/volé, tu es responsable.

### Plan de migration recommandé

| Phase | Hébergement | Coût/mois |
|---|---|---|
| 0–10 utilisateurs (beta) | Chez toi, 1 serveur | ~0 € |
| 10–100 utilisateurs (premiers payants) | **Hetzner serveur dédié** (AX42, 64 GB RAM) | ~50 € |
| 100–1000 utilisateurs | Hetzner dédié + serveur backup + Backblaze | ~100–150 € |
| > 1000 utilisateurs ou contrat enterprise | Cluster (2-3 dédiés Hetzner) + Postgres répliqué | ~300–500 € |

Hetzner = excellent rapport qualité/prix, basé en Allemagne (bien pour RGPD), réputé chez les devs européens. OVH, Scaleway sont aussi des options.

**Ne migre pas trop tôt.** Reste chez toi tant que ça ne te coûte pas plus cher en bugs et en pertes de prospects que ce qu'un dédié te coûterait.

---

## 8. Roadmap pragmatique — ordre des choses

Pour éviter l'erreur classique de vouloir tout faire en même temps.

### Semaines 1–2 : fondations

- Repo Git, structure Django avec apps découpées
- PostgreSQL local via Docker
- Modèle `User`, `Organization`, `Membership` (multi-tenant dès le départ — c'est dur à rétrofitter)
- Auth Django + Argon2
- Frontend React + Vite + TanStack Query + un wrapper API
- 1 endpoint qui marche bout en bout (`GET /api/v1/me`)
- `.env`, `DEBUG=False` testé, secret management correct

### Semaines 3–8 : domaine métier

- Modèles `Athlete`, `Exercise`, et la base du `Program` (phases, semaines, séances, prescriptions)
- API REST + serializers
- Frontend : connexion, dashboard, vue athlète, début du program builder
- **Tests unitaires** sur la logique métier de progression (c'est là qu'est ton edge — testes-la sérieusement)
- Tests cross-tenant dans la CI

### Mois 3 : durcir

- HTTPS via Caddy + Let's Encrypt
- Sentry branché
- Backups automatisés + restore testé
- Endpoint `/health` + Uptime Kuma
- Premier déploiement sur ton serveur perso
- Premiers beta-testeurs (2-3 coachs amis)

### Mois 4–6 : adoption initiale

- Itérer sur les retours coachs
- Ajouter Redis + Celery quand un job dépasse 200ms
- Logs centralisés si le volume le justifie
- Préparer la migration Hetzner

### Plus tard, quand le signal commercial le justifie

- App mobile React Native (consomme la même API)
- Cluster 2 instances + load balancing
- Réplication Postgres lecture
- Plan enterprise (DB séparée, SLA, etc.)

---

## Anti-patterns à éviter (résumé)

1. Commencer en microservices.
2. Coder sans tests sur la logique métier de progression.
3. Skipper le multi-tenant "pour aller plus vite" (c'est l'erreur la plus chère à corriger après).
4. Backups non testés.
5. `DEBUG=True` en prod, secrets en clair.
6. Stocker l'état en mémoire de process.
7. Sur-architecturer pour 10 000 users avant d'en avoir 10.
8. Sous-architecturer la sécurité parce que "on n'a personne de mal intentionné encore".

---

## Ce que je n'ai pas couvert (et qu'on peut creuser plus tard)

- Internationalisation (i18n) — Django + react-i18next, pas urgent.
- Tarification & facturation (Stripe).
- Mobile app (React Native + Expo).
- Email transactionnel (Postmark, Mailgun, Resend).
- Analytics produit (Plausible self-hosted, ou PostHog).
- Documentation technique interne (ADRs — Architecture Decision Records, fortement recommandé dès le départ pour ne pas oublier *pourquoi* tu as choisi telle techno).

---

*Document généré pour TrainForge — Ben Couture (couture.benj@gmail.com) — révisé 2026-05-18.*
