# 2. hét, lépésről lépésre

Kiegészíti: [`01-megvalositasi-terv.md`](01-megvalositasi-terv.md)
Időszak: 2026-09-25 — 2026-10-01

A 2.1–2.3 pont kész: az Azure-fiók megvan, a `szakdoga2-rg` erőforráscsoport
Terraformból épül (swedencentral, `Standard_B2s_v2`, 1-es zóna), a gépen a
cloud-init feltelepítette a k3s-t, és a laptopról a
`KUBECONFIG=~/.kube/szakdoga-azure.yaml kubectl get nodes` egy `Ready`
csomópontot mutat.

---

## 2.4 — A platform átköltöztetése

**Mit csinálunk.** A `platform/compose.yaml`-ból a Gitea, az act_runner és a
registry felmegy a mérőgépre, és igazoljuk, hogy a k3s fürt le tud húzni képet
a gépen futó registryből.

**Mit NEM csinálunk.** A megfigyelhetőségi szolgáltatások (Prometheus, Grafana,
Loki, Alloy, cAdvisor, node-exporter) maradnak — azok a 3.4 pontban kerülnek át,
és ott nem is így: a mostani cAdvisor- és node-exporter-beállítások a Docker
Desktop macOS-beli virtuális gépéhez vannak igazítva, Linuxon mások kellenek.
Ezért van a `platform/compose.azure.yaml`: profil mögé teszi őket, így a
`docker compose up -d` hármat indít, nem kilencet. A 8 GB-os gépen, amin a k3s
és maguk a buildek is futnak, ez nem esztétikai kérdés.

**Két terminál kell.** Az egyikben a laptopod van (a repó gyökerében), a
másikban a gép. Ahol nem egyértelmű, ott oda van írva, melyik.

---

### 1. lépés — A cím és az alapállapot *(laptop)*

```bash
cd ~/Documents/Szakdolgozat/MilanProjA-Szakdoga
terraform -chdir=terraform output -raw public_ip; echo
KUBECONFIG=~/.kube/szakdoga-azure.yaml kubectl get nodes
```

Ha a `kubectl` nem látja a fürtöt, ne lépj tovább: a 2.3 kész-feltétele az,
hogy lássa.

---

### 2. lépés — A platform felmásolása *(laptop)*

```bash
./scripts/platform-sync.sh
```

A szkript a `platform/` mappát tükrözi a gép `~/platform/` könyvtárába (a
`.env` kimarad, az a gépen készül), és felviszi a `verify-azure-platform.sh`
ellenőrzőt is. Egy irányba másol: a repó a forrás. Ha a gépen javítasz valamit,
vidd vissza a repóba, különben a következő futás felülírja.

---

### 3. lépés — Belépés és józansági ellenőrzés *(gép)*

```bash
ssh azureuser@$(terraform -chdir=terraform output -raw public_ip)

docker version --format '{{.Server.Version}}'
docker compose version
ls ~/platform
sudo k3s kubectl get nodes
```

Ha a `docker version` jogosultsági hibát ad: a cloud-init hozzáadott a `docker`
csoporthoz, de a *már megnyitott* munkamenet ezt nem tudja. Lépj ki, lépj be
újra (`exit`, majd megint `ssh`).

Egy dolgot érdemes itt megnézni, mert később órákat vihet el: a Docker és a k3s
ugyanazon a gépen saját iptables-szabályokat írnak.

```bash
docker run --rm busybox:1.36 ping -c1 1.1.1.1
```

Ha ez nem megy, a konténerek kifelé menő forgalma az, ami elromlott, nem a
compose-fájl — ezt jegyezd fel, és szólj, mielőtt tovább javítanál.

---

### 4. lépés — A `.env` a gépen *(gép)*

```bash
cd ~/platform
cp .env.example .env
sed -i 's/^GITEA_RUNNER_NAME=.*/GITEA_RUNNER_NAME=projecta-azure-runner/' .env
```

A tokent még nem tudjuk — az a Gitea elindulása után keletkezik. A többi érték
(képverziók, portok) mehet úgy, ahogy van. A `.env` a gépen sem kerül gitbe:
a `platform/.env` a repóban is ki van zárva.

---

### 5. lépés — Gitea és registry indítása *(gép)*

```bash
cd ~/platform
docker compose -f compose.yaml -f compose.azure.yaml up -d gitea registry
docker compose -f compose.yaml -f compose.azure.yaml ps
```

A runner még nem indul, mert regisztrációs token nélkül nincs mit csinálnia.

Várd meg, amíg a Gitea egészségesre vált (`healthy` a `ps` kimenetében), aztán:

```bash
curl -fsS http://localhost:3000/api/healthz; echo
curl -fsS http://localhost:5001/v2/; echo
```

**Miért nem a böngészőből.** A publikált portok a 127.0.0.1-re kötnek, ahogy a
laptopon is — a registrynek nincs hitelesítése, és ez a gép már publikus
IP-címen ül. A felület SSH-alagúton át érhető el (8. lépés), nem a tűzfalon át.

---

### 6. lépés — Admin felhasználó és runner-token *(gép)*

A laptopon a Gitea a webes telepítővarázslón keresztül állt be. Itt nem:
a `compose.azure.yaml` az `INSTALL_LOCK`-kal kikapcsolja, így a `terraform
destroy` + `apply` után sem marad benne kattintós lépés.

```bash
docker exec -u git projecta-gitea gitea admin user create \
  --admin --username milan --email milan.takacs24@gmail.com \
  --password 'ide-egy-erős-jelszót' --must-change-password=false
```

Aztán a token, egyből a `.env`-be:

```bash
TOKEN=$(docker exec -u git projecta-gitea gitea actions generate-runner-token | tr -d '\r\n')
echo "$TOKEN"
sed -i "s|^GITEA_RUNNER_REGISTRATION_TOKEN=.*|GITEA_RUNNER_REGISTRATION_TOKEN=${TOKEN}|" ~/platform/.env
grep RUNNER ~/platform/.env
```

*Ha a `gitea admin user create` azzal áll meg, hogy nincs adatbázis vagy nincs
konfiguráció:* állj meg itt. A B terv a webes telepítő (8. lépés alagútja, majd
`http://localhost:3000` a böngészőben, és a token a **Site Administration →
Actions → Runners** alól), de előbb nézzük meg, mit írt a
`docker logs projecta-gitea`.

---

### 7. lépés — A runner indítása *(gép)*

```bash
cd ~/platform
docker compose -f compose.yaml -f compose.azure.yaml up -d act-runner
docker logs -f projecta-act-runner
```

Sikeres regisztráció után a napló azt írja, hogy a runner regisztrált és
figyeli a feladatokat (`Ctrl-C` a követés leállítása, a konténer fut tovább).

Ha a regisztráció bukik és javítás után újrapróbálnád, a runner a már elmentett
állapotot látja; ilyenkor a saját kötetét el kell dobni:

```bash
docker compose -f compose.yaml -f compose.azure.yaml rm -sf act-runner
docker volume rm projecta-runner-data
```

---

### 8. lépés — A kész-feltétel ellenőrzése *(gép)*

```bash
~/verify-azure-platform.sh
```

Ez a 2.4 pont kész-feltétele futtatható alakban. Sorban: a három konténer fut;
a Gitea és a registry válaszol; a k3s containerd-konfigurációjában tényleg ott
van a `localhost:5001` tükör (amit a cloud-init `registries.yaml`-ja írt elő);
felnyom egy próbaképet a registrybe, **törli a gép Docker-gyorsítótárából**,
majd `imagePullPolicy: Always` beállítással elindít belőle egy podot. Ez a
törlés a lényeg: nélküle a teszt csak annyit bizonyítana, hogy a kép megvan
valahol a gépen, nem azt, hogy a fürt a registryből szedte.

A kimenetet mentsd el a bizonyítékok közé:

```bash
~/verify-azure-platform.sh 2>&1 | tee ~/2.4-verify.txt
```

Laptopról lehozni:

```bash
scp azureuser@$(terraform -chdir=terraform output -raw public_ip):2.4-verify.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify.txt
```

**A Gitea felülete** (nem kész-feltétel, de érdemes megnézni, hogy a runner
zölden látszik-e) — laptopról:

```bash
ssh -L 3000:127.0.0.1:3000 -L 5001:127.0.0.1:5001 \
  azureuser@$(terraform -chdir=terraform output -raw public_ip)
```

Amíg ez az ablak nyitva van, a `http://localhost:3000` a gépen futó Gitea.

---

#### Amit a 3. ellenőrzés kihozott — és ami emiatt változott

A `registries.yaml`, amit a cloud-init kiírt, **nem csinál semmit ezen a
fürtön.** k3s v1.36.4 alatt a fájlból egyetlen sor sem került a generált
containerd-konfigurációba, a kép letöltése mégis sikerült; a fájl átnevezése és
a k3s újraindítása után is sikerült. Ez utóbbi a negatív próba, és ez dönti el:
a magyarázat a containerd alapértelmezése, amely a loopback-címre mutató
registryt kivételként kezeli és TLS nélkül is elfogadja.

Következmény: a `terraform/cloud-init.yaml`-ból a `write_files` blokk kikerült,
a helyén a megállapítás áll kommentben. A 4.5-ben nem szabad azt írni, hogy a
fürt a Terraform registry-beállítása miatt éri el a registryt — attól éri el,
hogy ugyanazon a gépen fut. Ez a D5 döntés melletti érv, nem egy külön
konfigurációé.

Két bizonyítékfájl tartozik hozzá, a laptopra lehozva:

```bash
IP=$(terraform -chdir=terraform output -raw public_ip)
scp azureuser@$IP:2.4-verify.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify.txt
scp azureuser@$IP:2.4-verify-registries-nelkul.txt \
  szakdolgozat/bizonyitek/03-platform-koltoztetes-verify-registries-nelkul.txt
```

### 9. lépés — Rögzítés *(laptop)*

A [`bizonyitek/03-platform-koltoztetes.md`](bizonyitek/03-platform-koltoztetes.md)
vázába írd be, ami eltért a leírtaktól, és commitold a repó változásait
(`platform/compose.azure.yaml`, `scripts/platform-sync.sh`,
`scripts/verify-azure-platform.sh`, ez a fájl).

---

### Ami a 2.4-gyel NEM lett kész, és tudni kell róla

1. **A chart még nem a registryre mutat.** A `chart/values.yaml`-ban a kép
   `flaskapp` és `frontend`, előtag nélkül — ez a k3d-s fejlesztésre volt jó,
   ahol az images kézzel voltak betöltve a fürtbe. Az Azure-os fürtön
   `localhost:5001/projecta-flask` és `localhost:5001/projecta-frontend` kell.
   Ez a 2.5 első lépése, mert a kézi telepítési folyamat leírása már ezzel
   fog menni.
2. **A tűzfal 3000-es szabálya feleslegessé vált.** A Gitea a loopbackra köt,
   tehát a szabály nem nyit meg semmit — de egy védésen az "ami nyitva van,
   annak indoka van" elv szerint jobb, ha nincs ott. A `terraform/main.tf`
   `http-from-my-ip` szabályából kivehető; a 80/443 marad az alkalmazásnak.
3. **A CI és a mért fürt egy gépen osztozik** (D5 döntés). Most, hogy a runner
   tényleg ott fut, ez már nem elméleti: a build terheli a fürtöt. A 6.5-ben ezt
   ki kell mondani, és a mérésben az a helyes érvelés, hogy ez a *kézi* oldalnak
   kedvez, tehát a kimutatott javulás alsó becslés marad.
