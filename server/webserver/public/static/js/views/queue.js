var QueueView = Backbone.View.extend({
  song_template: Handlebars.compile($('#template-queue-song').html()),

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model.get('songs'), "change add remove reset swap", this.render);
      this.listenTo(this.model, "change", this.render);
    }
    this.songViews = [];
    this.render();
  },

  render: function() {
    for (var i = 0; i < this.songViews.length; i++) {
      this.songViews[i].remove();
    }
    var curr = this.model.get('current');
    var $ul = this.$el.find('ul.queue-songs');
    $ul.empty();
    var songs = this.model.get('songs');
    if (songs.length > 0) {
      var pos = 0;
      songs.each(function(song) {
        var songView = new SongView({
          template: this.song_template, 
          model: song, 
          meta: {
            current: curr == pos,
            pos: pos,
            first: pos == 0,
            last: pos == songs.length - 1
          }
        });
        pos++;
        this.songViews.push(songView);
        $ul.append(songView.el);
      }.bind(this));
      $ul.sortable({
        placeholder: '<li class="placeholder song" style="height:35px"></li>',
        vertical: false,
        nested: false,
        onDrop: function ($item, container, _super, event) {
          // default functionality
          $item.removeClass("dragged").removeAttr("style")
          $("body").removeClass("dragging")
          // custon functionality
          var song_lis = this.$el.find('ul.queue-songs>li').get();
          var to = song_lis.indexOf($item[0]);
          var from = $item.find('div.song').attr('data-pos');

          // A song has been moved from 'from' to 'to'
          // we make the first few changes silently and only the last one triggers a re-draw
          var songs = this.model.get('songs');
          var song = songs.at(from);
          songs.remove(song, {silent: true});
          // if we move the current song, we need to update the position of the current song
          var current = this.model.get('current');
          if (from < current && to >= current) {
            this.model.set('current', current - 1, {silent: true});
          } else if (from > current && to <= current) {
            this.model.set('current', current + 1, {silent: true});
          } else if (from == current) {
            this.model.set('current', to, {silent: true});
          }
          songs.add(song, {at: to});
        }.bind(this)
      });
    }
  }
});
