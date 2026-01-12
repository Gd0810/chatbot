document.addEventListener('DOMContentLoaded', function () {
    const workspaceSelect = document.querySelector('#id_workspace');
    if (!workspaceSelect) return;

    const aiFields = [
        '.field-ai_provider',
        '.field-ai_model',
        '.field-ai_api_key'
    ];

    function toggleAiFields(show) {
        aiFields.forEach(selector => {
            const row = document.querySelector(selector);
            if (row) {
                row.style.display = show ? '' : 'none';
            }
        });
    }

    function checkWorkspacePlan(workspaceId) {
        if (!workspaceId) {
            toggleAiFields(false);
            return;
        }

        fetch(`/bots/api/workspace-plan/${workspaceId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                toggleAiFields(data.includes_ai);
            })
            .catch(error => {
                console.error('Error fetching plan details:', error);
            });
    }

    workspaceSelect.addEventListener('change', function () {
        checkWorkspacePlan(this.value);
    });

    // Initial check
    if (workspaceSelect.value) {
        checkWorkspacePlan(workspaceSelect.value);
    } else {
        toggleAiFields(false);
    }
});
