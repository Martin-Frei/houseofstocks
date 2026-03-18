// HouseofStocks — Theme Toggle
// Speichert Hell/Dunkel Präferenz im localStorage
// TODO V3: User-Präferenz in Supabase/AWS speichern wenn eingeloggt

(function() {
  const saved = localStorage.getItem('hos-theme');
  if (saved === 'light') {
    document.getElementById('hos-body').classList.add('light');
  }
})();

function toggleTheme() {
  const body = document.getElementById('hos-body');
  body.classList.toggle('light');
  localStorage.setItem('hos-theme', body.classList.contains('light') ? 'light' : 'dark');
}
