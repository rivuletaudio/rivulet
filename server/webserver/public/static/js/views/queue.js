var QueueView = Backbone.View.extend({
  song_template: Handlebars.compile($('#template-queue-song').html()),
  placeholder_template: Handlebars.compile($('#template-placeholder-song').html()),

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model.get('songs'), "change add remove reset swap", this.render);
      this.listenTo(this.model, "change", this.render);
    }
    this.songViews = [];
    this.render();
  },

  // check if we are in radio mode and ready to take the next song into the queue
  add_queued_song_if_ready: function(){
    console.log('[] ready?');
    var curr = this.model.get('current');
    var songs = this.model.get('songs');
    var last = songs.length-1;
    if (last == -1) {
      console.log('[] no songs');
      return;
    }
    var model = this.model;
    var radio = model.get('radio');
    if (radio) {
      console.log('[] is in radio mode');
      var radio_song = model.get('radio-song');
      // is there a radio song?
      if (radio_song) {
        console.log('[] has radio song');
        var sources = model.get('radio-song').get_song_sources();
        // are we ready for the song?
        if (curr == last) {
          console.log('[] curr is last');
          // is the song ready for us?
          if (sources && sources.get('sources').length) {
            console.log('[] sources avaiable');
            this.model.add_last(radio_song);
            this.model.trigger('next_song_request');
          }
        }
      }
    }
  },

  render: function() {
    for (var i = 0; i < this.songViews.length; i++) {
      this.songViews[i].remove();
    }
    var curr = this.model.get('current');

    this.add_queued_song_if_ready();

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
        itemSelector: 'li.sortable',
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
          this.model.move_from_to(from, to);
        }.bind(this)
      });
    }

    if (this.model.get('radio')) {
      console.log('radio-song', this.model.get('radio-song'));
      var song = this.model.get('radio-song');
      if (song) {
          if (this.placeholderSongView) {
            this.placeholderSongView.remove();
          }

          var songView = new SongView({
            template: this.placeholder_template, 
            model: song
          });
          this.placeholderSongView = songView;
          var li = this.placeholderSongView.el;
          $ul.append(li);
          $(li).removeClass('sortable');
      } else {
        $ul.append('<li><div class="song"><p><i class="glyphicon glyphicon-refresh spinner big-spinner"></i></p></div></li>"');
      }
    }
  }
});
