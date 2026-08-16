# Front statique (nginx)
# Build depuis la RACINE : docker build -f client/Dockerfile -t sorydiallo89/gitops-project:client-1 .

FROM nginx:1.27-alpine

COPY client/nginx.conf /etc/nginx/conf.d/default.conf
COPY client/ /usr/share/nginx/html/

RUN rm -f /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/nginx.conf

EXPOSE 80
