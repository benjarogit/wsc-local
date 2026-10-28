ARG PHP_VERSION=8.4
FROM php:${PHP_VERSION}-apache-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev libjpeg62-turbo-dev libpng-dev libwebp-dev libicu-dev libzip-dev \
    libxml2-dev libonig-dev libcurl4-openssl-dev libgmp-dev unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install -j4 bcmath curl exif gd gmp intl mbstring mysqli pdo_mysql soap xml zip \
    && a2enmod rewrite headers ssl \
    && rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /usr/local/bin/wsc-apache-entrypoint
RUN chmod 0755 /usr/local/bin/wsc-apache-entrypoint
WORKDIR /var/www/html
