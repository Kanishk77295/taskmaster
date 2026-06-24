/* TaskMaster — main.js
   Handles live task toggle without full page reload.
   Demonstrates: fetch API, async/await, DOM manipulation.
*/

document.addEventListener('DOMContentLoaded', () => {

  // ── Live checkbox toggle ──────────────────────────────────────────────────
  document.querySelectorAll('.toggle-check').forEach(cb => {
    cb.addEventListener('change', async function () {
      const taskId  = this.dataset.id;
      const taskRow = document.getElementById(`task-${taskId}`);

      try {
        const res  = await fetch(`/task/${taskId}/toggle`, { method: 'POST' });
        const data = await res.json();

        // Update progress bar without reload
        const fill  = document.getElementById('main-progress');
        const label = document.getElementById('progress-label');
        if (fill)  fill.style.width  = data.pct + '%';
        if (label) label.textContent = data.pct + '% complete';

        // Visually move row to done/pending appearance, then reload for full re-sort
        if (taskRow) {
          taskRow.style.opacity = '0.4';
          taskRow.style.transition = 'opacity .3s';
        }
        setTimeout(() => location.reload(), 350);

      } catch (err) {
        console.error('Toggle failed:', err);
        // Revert checkbox on failure
        this.checked = !this.checked;
      }
    });
  });

  // ── Auto-dismiss flash messages ───────────────────────────────────────────
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 3500);
  });

});
