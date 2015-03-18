var SearchResultsView = Backbone.View.extend({
  song_template: Handlebars.compile($('#template-search-results-song').html()),
  template: Handlebars.compile($('#template-search').html()),
  spinner: Handlebars.compile($('#template-spinner').html()),

  events: {
  },

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change:searching", this.render);
      this.listenTo(this.model.get('results'), "reset", this.render);
    }
    this.songViews = [];
    this.render();
  },

  page_init: function() {
    if (!this.show) {
      this.$el.html(this.template());
      this.render();
      this.show = true;
    }
  },

  page_off: function() {
    this.show = false;
    for (var i = 0; i < this.songViews.length; i++) {
      this.songViews[i].remove();
    }
    if (this.pqueue) {
      this.pqueue.cancel();
      delete this.pqueue;
    }
  },

  render: function() {
    if (!this.show) return;
    if (this.model.get('searching')) {
      this.$el.find('ul').html(this.spinner());
      this.was_searching = false;
    } else {
      for (var i = 0; i < this.songViews.length; i++) {
        this.songViews[i].remove();
      }
      var $ul = this.$el.find('ul');
      $ul.empty();
      if (this.pqueue) {
        this.pqueue.cancel();
        delete this.pqueue;
      }
      this.pqueue = new ParallelQueue(3);
      if (this.model.get('results').length > 0) {
        this.model.get('results').each(function(result) {
          var songView = new SongView({template: this.song_template, model: result});
          this.songViews.push(songView);
          $ul.append(songView.el);
          if (!this.was_searching) {
            this.pqueue.add(songView.sources_search.bind(songView), [null]);
          }
        }.bind(this));
        this.was_searching = true;
      } else {
        $ul.append('<p>No results.</p>');
      }
    }
  },

  search: function(term) {
    // Same way to persist the playlist tab
    // TODO: find a better way...
    $('#tab-title-search').attr('href', '#search/' + encodeURIComponent(term));

    if (this.last_term === term) {
      this.render();
    } else {
      this.last_term = term;
      this.model.search(term);
    }
  }
});
