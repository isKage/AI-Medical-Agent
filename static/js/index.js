document.getElementById('searchFromIndex').addEventListener('click', function () {
    const uid = document.getElementById('uidFromIndex').value.trim();
    if (uid) {
        window.location.href = `/history?uid=${encodeURIComponent(uid)}`;
    }
});