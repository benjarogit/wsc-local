<?php
// WoltLab derives cookie Domain from HTTP_HOST. For local projects it includes
// the non-standard port (for example "forum.localhost:8081"), which browsers
// reject as an invalid cookie domain. Keep the host and drop only that port.
if (PHP_SAPI !== 'cli') {
    header_register_callback(static function (): void {
        $headers = headers_list();
        $cookies = [];
        $changed = false;

        foreach ($headers as $header) {
            if (stripos($header, 'Set-Cookie:') !== 0) {
                continue;
            }

            $cookie = trim(substr($header, strlen('Set-Cookie:')));
            $updated = preg_replace_callback(
                '/(;\s*domain=)([^;:]+):\d+(?=;|$)/i',
                static fn (array $match): string => $match[1] . $match[2],
                $cookie
            );
            $changed = $changed || $updated !== $cookie;
            $cookies[] = $updated;
        }

        if ($changed) {
            header_remove('Set-Cookie');
            foreach ($cookies as $cookie) {
                header('Set-Cookie: ' . $cookie, false);
            }
        }
    });
}
