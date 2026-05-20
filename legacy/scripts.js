$(function() {
  // $('.ui.modal').modal('show');
  $('.project-item').on('click', function (event) {
    var $project = $(event.currentTarget);
    var $modal = $('.ui.modal');
    $('.header', $modal).html($('> .caption > a', $project).html());
    $('.full-description', $modal).html('');
    $('.full-description', $modal).html($('.full-description', $project).html());
    var gists = $('> .gist-list .gist-item', $project);
    $('.gists .menu *', $modal).remove();
    $('.gists .tab', $modal).remove();
    gists.each(function(index, gist) {
      var id = $(gist).data('id');
      var title = $(gist).html();
      $('<div class="item" data-tab="'+index+'">'+title+'</div>').appendTo($('.gists .menu', $modal));
      var $tab = $('<div class="ui bottom attached tab segment" data-tab="'+index+'"></div>').appendTo($('.gists', $modal));
      var $code = $('<code data-gist-id="' + id + '" data-gist-show-loading="false"></code>');
      $code.appendTo($tab).gist();
      setTimeout(function() {
        $(window).resize();
      }, 3000);
    });
    $('.menu .item').tab();
    $modal.modal({
      observeChanges: true
    }).modal('show');
  });
});
