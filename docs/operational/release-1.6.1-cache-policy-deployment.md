# Release 1.6.1 cache-policy deployment verification

- **Release:** 1.6.1 — Frontend Cache Policy Hardening
- **Change type:** PATCH
- **Database revision:** unchanged at `20260809_cargo_catalog_items`
- **Deployment type:** frontend-only configuration/package hardening
- **Production action:** not performed by release preparation

## Source-to-package mapping

`public/web.config` is the tracked authoritative source. Vite copies it byte-for-byte to `dist/web.config`; packaging then copies `dist/web.config` to the root of the immutable release folder.

## Browser verification without DevTools

1. Open the site in a normal browser session with DevTools closed.
2. Record the currently loaded JavaScript asset filename from the returned HTML.
3. Switch IIS to the immutable Release 1.6.1 folder.
4. Refresh normally.
5. Confirm the returned HTML references the 1.6.1 JavaScript asset.
6. Confirm the new JavaScript and CSS assets return HTTP 200.
7. Confirm neither a hard refresh nor **Disable cache** is required.
8. Reopen the page and confirm hashed assets may be served from browser cache safely.

## Server header verification

Run only after a separately authorized IIS switch:

```powershell
$base = "http://server.logisticmarket.ir"
$root = Invoke-WebRequest "$base/" -UseBasicParsing
$index = Invoke-WebRequest "$base/index.html" -UseBasicParsing
$js = Invoke-WebRequest "$base/assets/<1.6.1-js-file>" -UseBasicParsing
$css = Invoke-WebRequest "$base/assets/<1.6.1-css-file>" -UseBasicParsing
$manifest = Invoke-WebRequest "$base/site.webmanifest" -UseBasicParsing

[pscustomobject]@{
    RootStatus           = $root.StatusCode
    RootCacheControl     = $root.Headers["Cache-Control"]
    IndexStatus          = $index.StatusCode
    IndexCacheControl    = $index.Headers["Cache-Control"]
    IndexPragma          = $index.Headers["Pragma"]
    IndexExpires         = $index.Headers["Expires"]
    JsStatus             = $js.StatusCode
    JsCacheControl       = $js.Headers["Cache-Control"]
    CssStatus            = $css.StatusCode
    CssCacheControl      = $css.Headers["Cache-Control"]
    ManifestStatus       = $manifest.StatusCode
    ManifestCacheControl = $manifest.Headers["Cache-Control"]
}
```

Require application-shell responses to return `no-cache, no-store, must-revalidate`, `Pragma: no-cache`, and `Expires: 0`; hashed assets to return `public, max-age=31536000, immutable`; and the webmanifest to return `public, max-age=0, must-revalidate`. API responses must retain backend-defined caching and must never return the SPA shell.
