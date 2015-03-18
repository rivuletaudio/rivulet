var PlayerView = Backbone.View.extend({
  template: Handlebars.compile($('#template-player').html()),

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change", this.render);
    }
    this.render();
  },

  render: function() {
    // song changed
    if (!(this.model &&
        this.model.current_song() !== undefined &&
        this.model.get('currently_playing_song') !== undefined &&
        this.model.get('currently_playing_song') === this.model.current_song())) {
      // This branch is the big re-rendering and is taken only when the
      // current song changes. Otherwise we should not kill the audio element.
      if (this.model &&
          this.model.current_song() !== undefined &&
          this.model.current_song().get_song_sources() &&
          this.model.current_song().get_song_sources().get('sources').length) {

        var play_link = this.model.current_song().make_link('play');
        var data = this.model.current_song().toJSON();
        data.audio_src = play_link;
        
        if (this.player) {
          this.player.pause();
          this.player.src = "";
        }
        
        this.$el.empty().html(this.template(data));
        this.player = this.$el.find('audio')[0];
        this.model.set('currently_playing_song', this.model.current_song());
      } else {
        this.$el.empty().html(this.template());
      }

      // events
      this.delegateEvents();
      if (this.player) {
        this.player.onended = this.next.bind(this);
      }
    }

    // This happens every re-render regardless of whether or
    // not the current song changed

    if (this.model.get('shuffle')) {
      this.$el.find('.shuffle-btn').addClass('active');
    } else {
      this.$el.find('.shuffle-btn').removeClass('active');
    }

    if (this.model.get('repeat')) {
      this.$el.find('.repeat-btn').addClass('active');
    } else {
      this.$el.find('.repeat-btn').removeClass('active');
    }

    return this;
  },

  events: {
    "click .prev-btn":          "prev",
    "click .next-btn":          "next",
    "click .shuffle-btn":       "shuffle",
    "click .repeat-btn":        "repeat"
  },

  prev: function(e){
    e.preventDefault();
    App.play_queue.play_prev()
  },

  next: function(e){
    e.preventDefault();
    App.play_queue.play_next();
  },

  shuffle: function(e){
    e.preventDefault();
    this.model.set('shuffle', !this.model.get('shuffle'));
  },

  repeat: function(e) {
    e.preventDefault();
    this.model.set('repeat', !this.model.get('repeat'));
  }
});

