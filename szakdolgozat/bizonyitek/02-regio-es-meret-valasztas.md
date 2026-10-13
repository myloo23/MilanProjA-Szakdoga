# Miért swedencentral és Standard_B2s_v2

Rögzítve: 2026-09-21 · A 4.5 alfejezethez (Terraform) és a korlátok tárgyalásához

A régió és a gépméret nem preferencia alapján dőlt el, hanem azért, mert az
Azure for Students előfizetésen ez az egyetlen engedélyezett kombináció. A
levezetés, a valódi hibaüzenetekkel:

## 1. Régiókorlátozás

Az első `terraform apply` a `westeurope` régióban 403-mal állt meg:

```
RequestDisallowedByAzure: Resource 'szakdoga-vnet' was disallowed by Azure:
This policy maintains a set of best available regions where your subscription
can deploy resources.
```

Az előfizetésre házirend van érvényben. A lekérdezése:

```
az policy assignment list --disable-scope-strict-match \
  --query "[].{nev:displayName, param:parameters}" -o json
```

Engedélyezett régiók: `belgiumcentral`, `austriaeast`, `francecentral`,
`swedencentral`, `spaincentral`.

## 2. A gépméret nem kapacitás, hanem jogosultság kérdése

`austriaeast` és `francecentral` egyaránt 409-cel utasította el a
`Standard_B2ms`-t, majd a `Standard_B2s_v2`-t is:

```
SkuNotAvailable: The requested VM size for resource 'Following SKUs have failed
for Capacity Restrictions: Standard_B2s_v2' is currently not available in
location 'FranceCentral'.
```

A kvóta nem volt nulla (`az vm list-usage`: BS család 4 vCPU, Bsv2 család
10 vCPU), és a konkrét zóna kérése (`zone = "1"`) sem segített. A valódi okot
a tiltáslista mutatta meg:

```
az vm list-skus -l <régió> --resource-type virtualMachines --all \
  --query "[?name=='Standard_B2s_v2'].{meret:name, tiltas:to_string(restrictions[].reasonCode)}" -o table
```

Az öt engedélyezett régióban a vizsgált négy méretből mindegyik
`NotAvailableForSubscription` tiltás alatt állt, **egyetlen kivétellel**:
`swedencentral` + `Standard_B2s_v2` (üres tiltáslista). A rendszer tehát ott fut.

## 3. Ami ebből a dolgozatba tartozik

- A „0 Ft költségvetés" feltétele nem csak árkorlát: a hallgatói előfizetés
  régió- és termékkorlátokkal is jár, és ezek szabják meg a célkörnyezetet.
- A gép `Standard_B2s_v2` (2 vCPU, 8 GB), `swedencentral`, 1-es zóna. A
  Magyarországhoz legközelebbi engedélyezett régió (Bécs) nem volt használható.
- A hálózati késleltetés a méréstől független: a mérés mindkét oldala —
  a kézi és az automatizált — ugyanarra a fürtre dolgozik, tehát a távolság
  mindkét sorozatot azonos irányban érinti.

## 4. Egy mellékes, de tanulságos hiba

A régió- és méretpróbák során az erőforráscsoportot többször kellett törölni és
azonos néven újra létrehozni. Az Azure vezérlősíkja ettől sorozatosan olyan
erőforrásokat adott vissza 404-gyel, amiket másodpercekkel korábban maga hozott
létre (`Provider produced inconsistent result after apply: Root object was
present, but now absent`), és a Terraform state elcsúszott a valóságtól — egy
ponton a létező gép nem szerepelt a nyilvántartásban, és a `terraform import`
állította helyre.

A megoldás nem javítgatás volt, hanem új névtér (`szakdoga2-` előtag) és üres
state; ezzel az `apply` elsőre végigment, 8 erőforrással, hibátlanul. A state és
a valóság szétcsúszása, valamint az `import` mint helyreállító eszköz jó példa
a 4.5 alfejezetbe: a state nem a valóság, hanem nyilvántartás róla.
