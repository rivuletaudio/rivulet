var ExploreView = Backbone.View.extend({
  template: Handlebars.compile($('#template-explore').html()),

  events: {
    'click .add-playlist-link': 'add_playlist'
  },

  initialize: function() {
    if (this.model) {
      // This will never actually happen with static playlist recommendations
      this.listenTo(this.model, "change", this.render);
      this.listenTo(App.playlists, "change add remove reset", this.render);
      this.listenTo(App.recommended_playlists, "change add remove reset", this.render);
    }
    this.render();
  },

  page_init: function() {
    if (!this.show) {
      this.show = true;
      if (this.model.length === 0) {
        this.get_recommendation();
      }
      this.render();
    }
  },

  page_off: function() {
    this.show = false;
  },

  render: function() {
    if (!this.show) return;
    var model = this.model.toJSON();
    for (var m in model) {
      var playlist = model[m];
      if (App.playlists.pluck('title').indexOf(playlist.title) != -1) {
        model[m].added = true;
      }
      playlist.songs = playlist.songs.toJSON();
    };
    this.$el.html(this.template({playlists: model}));
  },

  get_recommendation: function() {
    $.get('/recommendation').success(function(data) {
      var res = JSON.parse(data).result;
      res.songs = new SongCollection(res.songs);
      App.recommended_playlists.add(new Playlist(res));
    });
  },
  
  add_playlist: function(e) {
    e.preventDefault();
    var $this = $(e.currentTarget);
    var id = $this.attr('data-id');
    App.playlists.add(this.model.at(id).toJSON());
    App.save_playlists();
  }
});
