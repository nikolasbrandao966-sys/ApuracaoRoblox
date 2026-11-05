// Eleições Roblox 2026 — interações da página
document.addEventListener('DOMContentLoaded', function () {

  // dropdown de eleições (cabeçalho)
  var btn = document.getElementById('electionBtn');
  var menu = document.getElementById('electionMenu');
  if (btn && menu) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.classList.toggle('aberto');
    });
    document.addEventListener('click', function () {
      menu.classList.remove('aberto');
    });
  }

  // botão de busca — filtra os cards de candidato pelo nome
  var btnBusca = document.getElementById('btnBusca');
  var busca = document.getElementById('buscaInput');
  if (btnBusca && busca) {
    btnBusca.addEventListener('click', function () {
      busca.hidden = !busca.hidden;
      if (!busca.hidden) {
        busca.focus();
      } else {
        busca.value = '';
        filtra('');
      }
    });
    busca.addEventListener('input', function () { filtra(busca.value); });
  }
  function filtra(texto) {
    var q = texto.trim().toLowerCase();
    document.querySelectorAll('.cand-card').forEach(function (card) {
      var nome = (card.dataset.nome || '').toLowerCase();
      card.style.display = nome.indexOf(q) !== -1 ? '' : 'none';
    });
  }

  // botão de informação — mostra/esconde o popover
  var btnInfo = document.getElementById('btnInfo');
  var pop = document.getElementById('infoPopover');
  if (btnInfo && pop) {
    btnInfo.addEventListener('click', function () { pop.hidden = !pop.hidden; });
  }

  // pré-visualização da foto no formulário de candidato
  var inputFoto = document.getElementById('fotoArquivo');
  var preview = document.getElementById('fotoPreview');
  var placeholder = document.getElementById('fotoPlaceholder');
  if (inputFoto && preview) {
    inputFoto.addEventListener('change', function () {
      if (inputFoto.files && inputFoto.files[0]) {
        preview.src = URL.createObjectURL(inputFoto.files[0]);
        preview.style.display = '';
        if (placeholder) placeholder.style.display = 'none';
      } else {
        preview.style.display = 'none';
        if (placeholder) placeholder.style.display = '';
      }
    });
  }

  // confirmação antes de excluir candidato
  document.querySelectorAll('form.confirmar').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm('Excluir este candidato? Essa ação não pode ser desfeita.')) {
        e.preventDefault();
      }
    });
  });

  // botões de turno do formulário (radio estilizado)
  document.querySelectorAll('.form-turno .turno-btn input').forEach(function (radio) {
    radio.addEventListener('change', function () {
      var grupo = radio.closest('.form-turno');
      grupo.querySelectorAll('.turno-btn').forEach(function (b) { b.classList.remove('ativo'); });
      radio.closest('.turno-btn').classList.add('ativo');
    });
  });
});
