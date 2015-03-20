var Source = Backbone.Model.extend({
});

var SourceCollection = Backbone.Collection.extend({
  model: Source
});

var SongSources = Backbone.Model.extend({
  initialize: function() {
    var sources = this.get('sources');
    if (!(sources instanceof Backbone.Collection)) {
      this.set({
        sources: new SourceCollection(this.get('sources'))
      });
    }
  },
  defaults: function() {
    return {
      selected_id: undefined,
      sources: new SourceCollection()
    };
  },
  get_selected_source: function() {
    var selected_id = this.get('selected_id');
    var sources = this.get('sources');
    
    if (selected_id >= 0) {
      return sources.at(selected_id);
    } else {
      return null;
    }
  },
  add_source: function(source) {
    var sources = this.get('sources');
    if (sources.length === 0) {
      this.set('selected_id', 0, {silent: true});
    }
    sources.add(source);
  }
});
