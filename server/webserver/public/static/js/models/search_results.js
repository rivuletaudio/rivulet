var SearchResults = Backbone.Model.extend({
  defaults: function(){
    return  {
      searching: false,
      results: new SongCollection()
    }
  },

  search: function(term){
    if (this.get('searching')) {
      this._search_promise.abort();
      delete this._search_promise;
    }

    this.set('searching', true);

    this._search_promise = $.get('search?q=' + encodeURIComponent(term)).success(function(data){
      var result = JSON.parse(data).result;
      this.get('results').reset(result);
      this.set('searching', false);
    }.bind(this)).fail(function(){
      this.set('searching', false);
    }.bind(this));
  }
});
