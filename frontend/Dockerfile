FROM nginx:alpine

# Static site -- no build step, just serve the files as-is.
# index.html / admin.html sit at the root, so nginx's default
# "serve index.html for /" behavior works with zero extra config.
COPY . /usr/share/nginx/html

EXPOSE 80