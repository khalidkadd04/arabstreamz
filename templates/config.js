function getManifestUrl() {
    const currentUrl = window.location.href;
    const baseUrl = currentUrl.split('/configure')[0];
    return `${baseUrl}/manifest.json`;
}

function copyManifestLink() {
    const link = getManifestUrl();
    if (navigator.clipboard) {
        navigator.clipboard.writeText(link).then(() => {
            showNotification('Lien copié ! Collez-le dans la barre de recherche des Addons de Stremio.');
        }).catch(() => {
            prompt('Copiez ce lien pour Stremio :', link);
        });
    } else {
        prompt('Copiez ce lien pour Stremio :', link);
    }
}

function installAddon() {
    const link = getManifestUrl();
    const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.protocol === 'http:';

    if (isLocal) {
        // En local HTTP, le protocole stremio:// force HTTPS et supprime le port, ce qui échoue.
        // On copie le lien et on explique où le coller.
        copyManifestLink();
        alert(
            "⚠️ Installation locale Stremio :\n\n" +
            "Le protocole automatique stremio:// ne fonctionne pas en HTTP local (il force https:// sans le port 3000).\n\n" +
            "✅ Le lien HTTP a été copié dans votre presse-papiers :\n" + link + "\n\n" +
            "👉 Dans Stremio : allez dans Addons > collez ce lien dans la barre 'Search addons' > appuyez sur Entrée !"
        );
    } else {
        // En production HTTPS
        const cleanedLink = link.replace(/^https?:\/\//, '');
        window.open(`stremio://${cleanedLink}`, "_blank");
    }
}

function showNotification(msg) {
    const notif = document.getElementById('notification');
    if (notif) {
        notif.innerText = msg;
        notif.style.display = 'block';
        setTimeout(() => {
            notif.style.display = 'none';
        }, 5000);
    } else {
        alert(msg);
    }
}

// Initialiser le champ avec le lien au chargement
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('manifest-input');
    if (input) {
        input.value = getManifestUrl();
    }
});
