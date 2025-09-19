#!/usr/bin/env bash

create_env_file() {
    touch .env
    echo "SECRET_KEY=${SECRET_KEY}" >> .env
    echo "DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}" >> .env
    echo "DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME}" >> .env
    echo "DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL}" >> .env
    echo "DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD}" >> .env
}

main(){
    create_env_file
}

main