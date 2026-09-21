# Munkanapló

Lépésenként három mondat: **mit csináltam**, **mi lett volna nélküle**, **mit
bizonyít**. Nem a dolgozat szövege, hanem a nyersanyag hozzá — és a védésre ez
az, amiből felkészülsz, mert itt a saját szavaiddal van leírva.

Legfrissebb elöl.

---

## 2.4 — A platform átköltöztetése (2026-09-21)

**Mit csináltam.** A Gitea, az act_runner és a registry felment az Azure-os
mérőgépre, és igazoltam, hogy a k3s fürt le tud húzni képet a gépen futó
registryből.

**Mi lett volna nélküle.** A registry a laptopomon maradt volna, ahhoz pedig a
felhős fürt nem fér hozzá: a pipeline felépítené a képet, de telepíteni nem
tudná sehová. Ez a D5 döntés gyakorlati része.

**Mit bizonyít.** Hogy a lánc két vége összeért: ahová a build tesz, onnan a
fürt vesz. A `03-platform-koltoztetes-verify.txt` a bizonyíték.

**Amit közben megtanultam.** Azt hittem, a cloud-init `registries.yaml`-ja miatt
működik a letöltés. Nem: a fájl tartalma meg sem jelent a containerd
konfigurációjában, és a fájlt elvéve is működött. A valódi ok az, hogy a
containerd a `localhost:` előtagú registryt kivételként kezeli, mert az
ugyanazon a gépen van. **Egy állítás akkor bizonyított, ha az ellenkezőjét is
megpróbáltam előállítani.**
