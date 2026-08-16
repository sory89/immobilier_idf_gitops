# Front statique (nginx)
# Build depuis la RACINE : docker build -f client/Dockerfile -t sorydiallo89/gitops-project:client-1 .

FROM nginx:1.27-alpine

# L'image upstream embarque openssl 3.3.3-r0, vulnerable (CVE-2026-31789).
# On met a jour les paquets systeme sans attendre une reconstruction amont.
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*

COPY client/nginx.conf /etc/nginx/conf.d/default.conf
COPY client/ /usr/share/nginx/html/

RUN rm -f /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/nginx.conf

EXPOSE 80
