FROM php:8.3-apache-bookworm

# WoltLab braucht: ctype, dom, exif, fileinfo, gmp, intl, libxml, mbstring,
# openssl, pdo, pdo_mysql, zlib, sowie gd oder imagick (mit WebP).
# ctype / fileinfo / openssl / zlib / libxml sind in diesem Image bereits enthalten.
# gd + imagick: beide mit WebP – WoltLab akzeptiert entweder; beides ist robuster.

RUN apt-get update && apt-get install -y --no-install-recommends \
    libicu-dev \
    libpng-dev \
    libjpeg62-turbo-dev \
    libwebp-dev \
    libfreetype6-dev \
    libzip-dev \
    libonig-dev \
    libxml2-dev \
    zlib1g-dev \
    libgmp-dev \
    libmagickwand-dev \
    pkg-config \
    unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-configure intl \
    && docker-php-ext-install -j$(nproc) \
        intl \
        gd \
        mysqli \
        pdo \
        pdo_mysql \
        zip \
        mbstring \
        xml \
        exif \
        dom \
        gmp \
    && pecl install imagick \
    && docker-php-ext-enable imagick \
    && a2enmod rewrite headers ssl \
    && echo "ServerName localhost" >> /etc/apache2/apache2.conf \
    && sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf \
    && sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /var/www/html
