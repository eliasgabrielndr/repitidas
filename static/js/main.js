// Funções auxiliares para a interface
document.addEventListener('DOMContentLoaded', function() {
    // Converter minutos para segundos nos formulários
    const minutesToSeconds = document.querySelectorAll('.minutes-to-seconds');
    minutesToSeconds.forEach(function(element) {
        element.addEventListener('change', function() {
            const minutes = parseInt(this.value) || 0;
            const targetId = this.dataset.target;
            document.getElementById(targetId).value = minutes * 60;
        });
    });

    // Inicializar tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
