# 2.4 — A platform átköltöztetése az Azure-os mérőgépre

Dátum: 2026-09-21
Gép: `szakdoga2-vm` (swedencentral, `Standard_B2s_v2`, 1-es zóna), Ubuntu 24.04, k3s v1.36.4+k3s1
Lépésről lépésre: [`../04-masodik-het-lepesrol-lepesre.md`](../04-masodik-het-lepesrol-lepesre.md)

Ez a fájl a levezetést rögzíti. A gépi bizonyíték a
`03-platform-koltoztetes-verify.txt` és a
`03-platform-koltoztetes-verify-registries-nelkul.txt`
(a `scripts/verify-azure-platform.sh` két futása).

---

## 1. Kiindulás

- A `platform/compose.yaml` a laptopon kilenc szolgáltatást indított; a 2.4
  hatóköre ebből három: Gitea, act_runner, registry. A megfigyelhetőség a 3.4
  pontra marad.
- A k3s-t a cloud-init telepítette, és a laptopról a `kubectl` látta a fürtöt
  (2.3 kész-feltétele).

## 2. Amit a repóban módosítottam

| Fájl | Miért |
|---|---|
| `platform/compose.azure.yaml` | Gitea telepítővarázsló kikapcsolása; a megfigyelhetőségi szolgáltatások `observability` profil mögé |
| `scripts/platform-sync.sh` | a `platform/` egyirányú tükrözése a gépre |
| `scripts/verify-azure-platform.sh` | a kész-feltétel futtatható alakban |
| `terraform/cloud-init.yaml` | a `registries.yaml` kiírása kikerült — lásd a 4. pontot |

## 3. A futtatás

A platform a leírt sorrendben elindult. A Gitea a webes telepítő nélkül,
`INSTALL_LOCK`-kal állt fel; az admin felhasználó és a runner regisztrációs
tokenje a `gitea` parancssori felületéről jött, tehát a platform üzembe
helyezésében nincs böngészős lépés.

Egy eltérés: a runner első regisztrációja után a szolgáltatás állapota már el
volt mentve a `projecta-runner-data` kötetben, ezért az újraregisztrációhoz a
kötetet is el kellett dobni, és új tokent kellett generálni. Ez a `04-` doksi
7. lépésében így is szerepel.

## 4. A registries.yaml — a 2.4 egyetlen érdemi megállapítása

A cloud-init a k3s telepítése előtt kiírta a
`/etc/rancher/k3s/registries.yaml` fájlt, amely a `localhost:5001` címet sima
HTTP-s tükörként hirdette meg. Az ellenőrzés három dolgot mutatott:

1. A fájl jelen volt, de **a generált containerd-konfigurációban nem jelent
   meg**: `sudo grep -rn "5001" /var/lib/rancher/k3s/agent/etc/` üres,
   `exit=1`. A k3s újraindítása után is üres maradt.
2. A fürt ennek ellenére lehúzta a képet a gépen futó registryből (87–302 ms,
   `imagePullPolicy: Always`, a kép a push után törölve a gép
   Docker-gyorsítótárából).
3. **Negatív próba:** a fájlt átnevezve (`registries.yaml.ki`) és a k3s-t
   újraindítva a letöltés változatlanul sikerült.

Következtetés: a letöltés nem a Terraform registry-beállításán múlik, hanem a
containerd alapértelmezésén, amely a loopback-címre mutató registryt
kivételként kezeli, és TLS nélkül is elfogadja. A fürt tehát **attól** éri el
a registryt, hogy ugyanazon a gépen fut — ez a D5 döntés következménye.

Amit ezzel tenni kell:

- a `write_files` blokk kikerült a `terraform/cloud-init.yaml`-ból, a helyén a
  megállapítás áll kommentben;
- a 4.5 (Terraform) alfejezetben a registry elérését **nem** a Terraform
  érdemének kell írni;
- ha a képhivatkozás valaha nem `localhost:` előtagú lesz (a gép neve vagy
  privát IP-címe), a kivétel nem érvényes: akkor a beállítás visszakerül, és
  külön ellenőrizni kell, hogy az adott k3s-verzió átvezeti-e a containerdbe.

Ez a megállapítás a dolgozatban többet ér, mint a sima "beállítottam és
működik": megmutatja, hogy az ellenőrzés nem a saját feltevésemet igazolta
vissza.

## 5. A kész-feltétel

> *Kész, ha:* a fürt le tud húzni egy képet a gépen futó registryből.

Teljesült: **igen**, mindkét futásban (a `registries.yaml`-lal és nélküle is).
