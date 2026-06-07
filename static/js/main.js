/**
 * ZapPro - JavaScript principal
 */

document.addEventListener('DOMContentLoaded', function () {
    // Toggle sidebar mobile
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        document.addEventListener('click', function (e) {
            if (window.innerWidth < 992) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // Auto-dismiss alerts após 5 segundos
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
});

/**
 * Polling do status WhatsApp
 */
function startWhatsAppPolling(statusUrl, onUpdate) {
    const interval = setInterval(function () {
        fetch(statusUrl, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (onUpdate) onUpdate(data);
            })
            .catch(function (err) {
                console.error('Erro ao verificar status:', err);
            });
    }, 3000);

    return interval;
}
