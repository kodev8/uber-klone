var indexIntersectionObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.remove('opacity-0', 'translate-y-32');
        entry.target.classList.add('opacity-100', 'translate-y-0');
        indexIntersectionObserver.unobserve(entry.target);
      } 
    });
  }, {rootMargin: '-50px',});
  
  document.querySelectorAll('.reveal').forEach((r) => {
    indexIntersectionObserver.observe(r);
  });
  
var backToTop = document.querySelector('.back-to-top');
  
  if (backToTop) {
  
    var backToTopObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          backToTop.classList.remove('opacity-0', 'translate-y-32');
        } else {
          backToTop.classList.add('opacity-0', 'translate-y-32');
        }
      });
    }, {rootMargin: '-50px',});
    
    backToTopObserver.observe(document.querySelector('.back-to-top-threshold'));
  
  }