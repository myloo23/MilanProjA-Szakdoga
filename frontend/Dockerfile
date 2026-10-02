# A frontend két lépcsőben épül. Az első lépcső (node) csak a fordításhoz kell:
# az `npm ci` a package-lock.json szerint, hash-ellenőrzéssel telepít, a Vite
# pedig statikus fájlokat fordít. A kész image-be ebből semmi nem kerül, csak a
# dist/ tartalma, ezért a Node és az npm-csomagok sérülékenységei a futó
# konténert nem érintik (a Trivy a futó lépcsőt vizsgálja, lásd ci.yml).
#
# Az alapképek digesttel rögzítettek, mint a backendnél: a címke (tag) egy
# mutató, amelyet a kiadó bármikor továbbléptethet, a digest maga a tartalom.
# Digest nélkül ugyanabból a commitból két különböző napon két különböző image
# épülhet. Léptetni csak a scripts/pin-base-images.sh-val szabad, mert az előbb
# lefuttatja a pipeline Trivy-kapuját az új alapképeken, és csak tiszta
# eredmény után írja át ezeket a sorokat.
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Nem root felhasználóval futó nginx; ezért figyel a 8080-as porton (nginx.conf).
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
