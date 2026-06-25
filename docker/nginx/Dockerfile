FROM nginx:1.27-alpine

# Drop the default config and use our project-specific one.
RUN rm /etc/nginx/conf.d/default.conf

COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
