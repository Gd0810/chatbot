function RedbotLoad(public_key) {
    const div = document.getElementById('redbot-chat');
    if (!div) return;

    const iframe = document.createElement('iframe');
    iframe.src = `http://localhost:8000/embed/widget/${public_key}?origin=${encodeURIComponent(window.location.origin)}`;
    iframe.style.position = 'fixed';
    iframe.style.bottom = '20px';
    iframe.style.right = '20px';
    iframe.style.width = '300px';
    iframe.style.height = '400px';
    iframe.style.border = 'none';
    iframe.style.zIndex = '9999';
    div.appendChild(iframe);
}