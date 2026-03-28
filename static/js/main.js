const domains = [
    "https://kashmirobserver.net",
    "https://thekashmiriyat.co.uk",
    "https://kashmirnews.in",
    "https://kashmirdespatch.com",
    "https://kashmirlife.net",
    "https://risingkashmir.com",
    "https://greaterkashmir.com",
    "https://asiannewshub.com",
    "https://thekashmirmonitor.net",
    "https://kashmirreader.com",
    "https://kashmirtimes.com",
    "https://newsvibesofindia.com",
    "https://kashmirvision.in"
];
function createLink(rel, href, crossorigin = false) {
    const link = document.createElement("link");
    link.rel = rel;
    link.href = href;
    if (crossorigin) {
        link.crossOrigin = "anonymous";
    }
    document.head.appendChild(link);
}
domains.forEach(domain => {
    createLink("preconnect", domain, true);
    createLink("dns-prefetch", domain);
});
