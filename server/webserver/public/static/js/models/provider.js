var Provider = Backbone.Model.extend({
  defaults: function() {
    return {
      title: 'Untitled',
      index: undefined,
      selected: undefined
    };
  },
});

var ProviderCollection = Backbone.Collection.extend({
  model: Provider
});
