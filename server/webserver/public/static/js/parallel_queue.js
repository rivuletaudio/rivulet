var ParallelQueue = function(max) {
  this.queue = [];
  this.parallel = 0;
  this.parallel_max = max;
};

ParallelQueue.prototype.add = function(func, args) {
  this.queue.unshift([func, args]);
  this.try_run();
};

ParallelQueue.prototype.try_run = function() {
  while (this.parallel_max > this.parallel && this.queue.length > 0) {
    var q = this.queue.pop();
    var f = q[0];
    var a = q[1];
    a.push(this.finish.bind(this));
    f.apply(this, a);
    this.parallel++;
  }
}

ParallelQueue.prototype.finish = function() {
  this.parallel--;
  this.try_run();
}

ParallelQueue.prototype.cancel = function() {
  this.queue = [];
}
