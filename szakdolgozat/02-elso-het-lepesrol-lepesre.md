# 1. hét, lépésről lépésre

Kiegészíti: [`01-megvalositasi-terv.md`](01-megvalositasi-terv.md)
Időszak: 2026-09-18 — 2026-09-24

Ez a fájl **csak az első hetet** bontja parancsokra. A 2. hét (Terraform, Azure)
akkor kerül ide, amikor idáig eljutottál — előbb nincs értelme, mert a
Terraform-kódot az fogja meghatározni, amit itt megépítesz.

**Munkamódszer.** Vágj egy `release/sprint4` ágat a `main`-ről, és azon belül
dolgozz `feature/*` ágakkal, ahogy eddig. A `docs/PLAN.md` kétszer is rögzíti,
hogy egy merge nem jutott ki a giteára és emiatt napokig nem futott CD — minden
push menjen ki **mindkét** távolira.

---

## 0. nap (ma) — az egyetlen dolog, ami nem tőled függ

Nyisd meg az **Azure for Students** fiókot az egyetemi e-mail-címeddel:
<https://azure.microsoft.com/en-us/free/students>. Bankkártya nem kell, a
hallgatói igazolás viszont eltarthat egy napig. 100 USD kredit, 12 hónap.

*Kész, ha:* belépsz a portálra, és látod a kreditet. Ha elakad, szólj — az
1. terv R1 pontja a B terv.

---

## 1. nap — fürt a gépeden, és az első pod

### 1.1 Eszközök

```bash
brew install k3d kubectl helm
k3d version && kubectl version --client && helm version
```

### 1.2 Fürt

```bash
k3d cluster create szakdoga --agents 1
kubectl get nodes
```

Két sort kell látnod, mindkettő `Ready`. Ha igen, van egy működő
Kubernetes-fürtöd. A `k3d cluster delete szakdoga` bármikor eldobja, és harminc
másodperc alatt újat csinálsz — ezen a héten nyugodtan rombolj.

### 1.3 Nézz körül

```bash
kubectl get pods -A
```

Ez a fürt saját szolgáltatásait mutatja (CoreDNS, Traefik, metrics-server). A
`-A` = minden névtérben. Amit te telepítesz, az alapból a `default` névtérbe megy.

### 1.4 Az első pod, kézzel

```bash
kubectl run proba --image=nginx --port=80
kubectl get pods
kubectl describe pod proba
kubectl logs proba
kubectl delete pod proba
```

A `describe` kimenetének az alja (`Events`) a legfontosabb dolog, amit ezen a
héten megtanulsz: **a Kubernetesben majdnem minden hiba ott van leírva.**

*A nap kész, ha:* a `kubectl get nodes` két `Ready` csomópontot mutat, és
elindítottál meg eltöröltél egy podot.

---

## 2. nap — a saját alkalmazásod a fürtben

### 2.1 Kép építése és betöltése

**Minden parancsot a repó gyökeréből futtass** (`cd
~/Documents/Szakdolgozat/MilanProjA-Szakdoga`). A git-parancsok máshonnan nem
találják a repót, és az ebből épülő tag üres lesz.

A k3d saját, elszigetelt Dockerben fut, ezért a gépeden épített kép nincs meg
neki. Be kell tölteni:

```bash
docker build -t flaskapp:dev .
k3d image import flaskapp:dev -c szakdoga
```

Ezt a két parancsot ezen a héten sokszor fogod futtatni. A 3. naptól egy
szkript veszi át (`scripts/dev-reload.sh`), ami ugyanezt csinálja, plusz
újraindítja a Deploymentet és kiírja, melyik verzió fut.

### 2.2 Manifest

`k8s/backend.yaml` néven (ez ideiglenes hely, a 6. napon Helm chart lesz belőle):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: flaskapp:dev
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 8000
```

**Amit ez leír:** a Deployment azt mondja, hogy ebből a képből mindig fusson két
példány. A `livenessProbe` az, amit a Dockerfile `HEALTHCHECK`-je csinált eddig:
ha a `/health` nem válaszol, a Kubernetes újraindítja a konténert. A
`readinessProbe` új: amíg a `/ready` nem válaszol, a pod **nem kap forgalmat** —
pont ez teszi lehetővé, hogy verzióváltásnál ne legyen kiesés. A Service egy
stabil belső név és IP a két pod elé; a podok jönnek-mennek, a Service marad.

### 2.3 Telepítés és ellenőrzés

```bash
kubectl apply -f k8s/backend.yaml
kubectl get pods -w          # Ctrl-C, ha mindkettő Running
kubectl port-forward svc/backend 8080:80
```

Másik terminálban:

```bash
curl localhost:8080/health
curl localhost:8080/
curl -X POST localhost:8080/echo -H 'content-type: application/json' -d '{"a":1}'
```

### 2.4 A kísérlet, ami miatt ez a nap van

```bash
kubectl get pods
kubectl delete pod <az-egyik-pod-neve>
kubectl get pods
```

A törölt pod helyett harminc másodpercen belül új indul. Te nem csináltál
semmit. **Ez a deklaratív működés, és ez a 2.5 alfejezet egyik bekezdése.**

Aztán:

```bash
kubectl scale deployment backend --replicas=5
kubectl get pods
kubectl scale deployment backend --replicas=2
```

*A nap kész, ha:* fut az alkalmazásod a fürtben, és el tudod mondani a
különbséget a Pod, a Deployment és a Service között.

---

## 3. nap — `/version` és build-metaadat

Ez a `docs/PLAN.md` 7. pontjának 5. tétele, és **a mérés elfogadási kritériuma
épül rá**: minden futtatásnál azt nézed, hogy a `/version` az új git SHA-t adja-e
vissza.

### 3.1 Dockerfile

A runtime szakaszba, a `USER appuser` elé:

```dockerfile
ARG GIT_SHA=dev
ENV APP_VERSION=${GIT_SHA}
LABEL org.opencontainers.image.revision=${GIT_SHA} \
      org.opencontainers.image.source="https://github.com/myloo23/<repo>" \
      org.opencontainers.image.title="ProjectA backend"
```

Ezzel az OCI-címkék (Phase 2 nyitott tétele) is megvannak.

### 3.2 A végpont

`app/app.py`-ba, a többi route mellé:

```python
@app.get("/version")
def version():
    return jsonify({"version": os.environ.get("APP_VERSION", "dev")})
```

Teszt hozzá a `tests/test_app.py`-ba — a 80%-os lefedettségi kapu él.

### 3.3 Teszt a végponthoz

A `/version`-re két teszt kell a `tests/test_app.py`-ba: beállított
`APP_VERSION` esetén azt adja vissza, enélkül pedig `dev`-et. Teszt nélkül a
80%-os lefedettségi kapu előbb-utóbb pirosra vált.

### 3.4 Építés SHA-val — és a tag csapdája

Itt van egy buktató, ami fél órát el tud venni. **Két különböző dolog van, és
összekeverhető:**

- a **tag** (`flaskapp:dev`, `flaskapp:a6a4d33`) az, ahogy a képet *megtalálod*;
- a **build-argumentum** (`--build-arg GIT_SHA=...`) az, amit a `/version`
  *visszamond*.

Ha csak SHA-val tageled a képet, a fürtben futó manifest viszont `flaskapp:dev`-et
keres, akkor a régi kép marad, és nem érted majd, miért nem változik a
`/version`. Ezért a fejlesztői hurokban **mindkét taget** rárakjuk ugyanarra a
képre:

```bash
./scripts/dev-reload.sh
```

Ez a szkript a repó gyökerében ezt csinálja: kiolvassa a git SHA-t (és
`-dirty`-t fűz hozzá, ha van nem commitolt változtatásod), épít
`--build-arg GIT_SHA=...`-val, `flaskapp:dev` és `flaskapp:<sha>` néven egyszerre,
betölti a fürtbe, újraindítja a Deploymentet, megvárja, és kiírja a futó
verziót.

A `-dirty` jelölés nem kozmetika: **a mérés futtatásait csak tiszta
munkakönyvtárból szabad indítani**, különben a telepített kép olyan verziószámot
állít magáról, ami nincs is benne.

A 6. naptól ez a probléma megszűnik, mert a Helm `--set image.tag=...`
intézi, élesben pedig minden telepítés saját, egyedi SHA-taget kap — soha nem
`latest`. Ez a `docs/adr/0002-build-once-push-to-registry.md` döntése, és a
mérés is erre épül.

*A nap kész, ha:* a `./scripts/dev-reload.sh` végén kiírt verzió megegyezik a
`git rev-parse --short HEAD` kimenetével, és a `ci.yml` build-lépése is átadja a
`--build-arg`-ot.

---

## 4. nap — adatbázis és CRUD

### 4.1 Függőség

A függőségeid hash-lockoltak, ezért nem elég a `pip install`:

```bash
# requirements.in-be: psycopg[binary]
pip-compile --generate-hashes --allow-unsafe requirements.in
```

(Az `--allow-unsafe` a `docs/DEVELOPMENT.md`-ben rögzített javítás — nélküle
kiesnek a `pip`/`setuptools` pinek.)

### 4.2 PostgreSQL a fürtben

`k8s/postgres.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
stringData:
  POSTGRES_USER: projecta
  POSTGRES_PASSWORD: valtoztasd-meg
  POSTGRES_DB: projecta
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          envFrom:
            - secretRef:
                name: db-credentials
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "projecta"]
            initialDelaySeconds: 5
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: postgres-data
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
```

**Három dolog, amit ez tanít, és a dolgozatba is megy:** a Secret elválasztja a
jelszót a manifesttől; a PVC miatt az adat túléli a pod halálát; a `Recreate`
stratégia azért kell, mert két Postgres-példány nem írhatja ugyanazt a
könyvtárat (szemben a backenddel, ahol a `RollingUpdate` a jó).

A backend a `postgres:5432` néven éri el — a Service neve a DNS-név a fürtön belül.

### 4.3 CRUD

Egy entitás (`note`: id, title, body, created_at), négy végpont: `POST /notes`,
`GET /notes`, `PUT /notes/<id>`, `DELETE /notes/<id>`. Táblalétrehozás
alkalmazásindításkor, ha nincs. Pytest mindegyikre.

*A nap kész, ha:* a `kubectl delete pod` a Postgres podján lefut, és az adatok
utána is megvannak.

---

## 5. nap — frontend

```bash
npm create vite@latest frontend -- --template react-ts
```

Egy oldal, ami listázza, létrehozza, módosítja és törli a jegyzeteket. Stílus:
amennyi öt perc alatt belefér. **Ez a nap egy nap, nem három.**

`frontend/Dockerfile`:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
```

Az `nginx-unprivileged` azért kell, mert a sima nginx-kép rootként indul, és a
projekt szabálya, hogy a konténer nem root (`docs/PLAN.md` 6. pont). Az
`nginx.conf`-ban a `/api` proxyzzon a `backend` Service-re, így a böngészőnek
nem kell tudnia a backend címéről, és nincs CORS-probléma.

Ehhez is kell `k8s/frontend.yaml` (Deployment + Service), a backendéhez hasonló,
`containerPort: 8080`-nal. Plusz egy Ingress, hogy a böngészőből egy címen
érhesd el mindkettőt — a k3d-ben a Traefik alapból ott van.

*A nap kész, ha:* böngészőből használható a teljes alkalmazás a fürtön keresztül.

---

## 6. nap — Helm chart

```bash
helm create chart
```

Ez generál egy vázat, amiben sok a felesleg. Töröld: `templates/tests/`,
`templates/hpa.yaml`, `templates/serviceaccount.yaml`. Ami marad, azt cseréld le
a saját manifestjeidre, és a változó részeket emeld ki `values.yaml`-be:

```yaml
image:
  repository: flaskapp
  tag: dev
replicaCount: 2
frontend:
  image:
    repository: frontend
    tag: dev
postgres:
  enabled: true
```

A manifestben pedig `{{ .Values.image.tag }}` és társai.

Próbák:

```bash
helm template chart | less                      # mit generálna, telepítés nélkül
helm upgrade --install projecta ./chart
helm upgrade --install projecta ./chart --set image.tag=abc1234
helm history projecta
helm rollback projecta 1
```

**Ez a nap a legfontosabb a pipeline szempontjából**, mert a 3. héten a
`ci.yml`-ben az Ansible-lépés helyére pontosan a `helm upgrade --install` sor
kerül, `--set image.tag=$GITHUB_SHA`-val.

*A nap kész, ha:* egyetlen paranccsal telepíted az egész alkalmazást, verziót
tudsz váltani `--set`-tel, és a `helm rollback` visszaáll az előzőre.

---

## 7. nap — írás és rendrakás

Fél nap írás, amíg friss:

- **3.5** — architektúra, a mostani Docker Compose-os és az új
  Kubernetes-alapú felállás szembeállítva.
- **3.6** — eszközválasztás: miért k3s, miért Helm, miért nem Next.js. Az
  `01-megvalositasi-terv.md` D1–D8 pontjai a nyersanyag.
- **Két új ADR** a `docs/adr/` mintájára: `0008-k3s-over-managed-kubernetes.md`
  és `0009-helm-replaces-ansible-for-deployment.md`. Az ADR-ek megírása menet
  közben a 3.8 alfejezet kész anyaga.

Fél nap rendrakás: PR, CI zöld, `README.md` és `PLAN.md` frissítése — a
"deploy target: local Docker host" mondat már nem igaz.

---

## Ha elakadsz

**`ImagePullBackOff`** — a fürt nem találja a képet. Majdnem mindig az
elfelejtett `k3d image import`, vagy hiányzik az `imagePullPolicy: IfNotPresent`.

**`CrashLoopBackOff`** — a konténer elindul és meghal. `kubectl logs <pod>
--previous` megmutatja, miért.

**`Pending` állapotban ragadt pod** — nincs elég erőforrás, vagy a PVC nem
kötődött. `kubectl describe pod <név>`, az `Events` szakasz megmondja.

**Bármi más** — `kubectl describe` és `kubectl get events --sort-by=.lastTimestamp`.
Ha fél óra után sem világos, kérdezz; az 1. terv R2 pontja pont erről szól.
