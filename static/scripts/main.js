

//  links a given elleemtn to the item it shows on hover
function linkHoverShow(element, to_hover) {
    element?.addEventListener('mouseenter', ()=>  {
        ht = setTimeout(()=>{
            to_hover?.classList.remove('invisible')
            element?.focus()
    }, 500)

    } )

    element?.addEventListener('mouseleave', ()=> {

        if(!to_hover.matches(':hover')){
        clearTimeout(ht)
        to_hover?.classList.add('invisible')}
    })

    to_hover?.addEventListener('mouseleave', ()=> {

        if(!element.matches(':hover')){
        clearTimeout(ht)
        to_hover?.classList.add('invisible')}
    })

    let isMobile = false;

    element?.addEventListener('touchstart', () => {
        isMobile = true;
    });

    element?.addEventListener('click', (event) => {
        if (isMobile) {
            event.preventDefault()
            // Handle the click action for mobile devices
            if (to_hover.classList.contains('invisible')) {
                to_hover.classList.remove('invisible');
            } else {
                to_hover.classList.add('invisible');
            }
            isMobile = false; // Reset the flag
        }
    });
}

// docuemnt to hide
function dth(triggerElement, target) {
    let t = target instanceof HTMLElement ? target : triggerElement.target.querySelector(target)
    // console.log(event.target, 'from dth')
    if (t){
    t.classList.toggle('invisible')

    document.addEventListener("click", (e) => {
    if (!triggerElement.contains(e.target)) {
        t.classList.add("invisible");
    }
    });
}
}

// send with params
function swp() {
    let url = new URL(window.location.href)
    let params = new URLSearchParams(url.search)
    return params
}

function handleCustomInputs() {

    console.log
    document.querySelectorAll('.custom-input-group')?.forEach(customInputGroup => {

        let customInput = customInputGroup.querySelector('.custom-input-x')
        customInput.addEventListener('input', (event) => {
            let inlineError = customInputGroup.querySelector('.inline-error')
            if (inlineError && inlineError.innerHTML !== '') {
                inlineError.innerHTML = ''
            }
            
        })

        let searchable = customInputGroup.querySelector('.searchable')
        if (searchable) {
            let clearIcon = customInputGroup.querySelector('.clear-icon')
            let resultWrapper = searchable.closest('.results-wrapper')
            let resultParentContainer = resultWrapper.querySelector('.results-parent-container')
            let resultContainer = resultWrapper.querySelector('.results-container')
            
            searchable.addEventListener('focus', (event) => {
                resultParentContainer.classList.remove('invisible')
            })

            document.addEventListener("click", (e) => {
                if (e.target.contains(searchable)) return
                resultParentContainer.classList.add('invisible')
                });
            
            clearIcon?.addEventListener('click', (evt) => {
                searchable.value = ''
                resultContainer.innerHTML = ''
                resultParentContainer.classList.add('invisible')

                if (clearIcon.classList.contains('dropoff')){
                    document.querySelector('#marker-dropoff')?.remove()
                }else if (clearIcon.classList.contains('pickup')){
                    document.querySelector('#marker-pickup')?.remove()

                }

                // hide map clickers
                document.querySelectorAll('.map-clicker').forEach(clicker => {
                    clicker.classList.add('hidden')
                    clicker.classList.remove('flex')
                })

                clearIcon?.classList.add('invisible')
                let f = clearIcon.closest('form').querySelector('.form-submitter')
                if (f) f.disabled=true

            })

            searchable.addEventListener('input', (evt) => {
                clearIcon?.classList.toggle('invisible', evt.target.value.length === 0)
                document.querySelectorAll('.results-wrapper').forEach(wrapper => { 
                    if (wrapper != resultWrapper) {
                        otherResContainer = wrapper.querySelector('.results-parent-container')
                        if (!otherResContainer.classList.contains('invisible')) {
                            // console.log('closing other results container', wrapper)
                            wrapper.querySelector('.results-parent-container').classList.add('invisible')
                        }
                    
                    }
                })
            })
        }

        let numbered = customInputGroup.querySelector('.numbered')
        if (numbered) {
            numbered.addEventListener('input', (e) => {
                let value = e.target.value
                if (value.slice(-1).match(/\D/)) {
                    e.target.value = value.replace(/[^0-9]/g, '');
                    value = e.target.value
                }
                
               
            
            })
            
        }
      
        // let eye ico control if text input is password or text
        let eyeIcon = customInput.parentNode.querySelector('.eye-icon')
        if(eyeIcon){
          eyeIcon.addEventListener('click', (e)=> {
      
            e.preventDefault();
              if(customInput.type == 'password') {
                  eyeIcon.classList.remove('fa-eye-slash')
                  eyeIcon.classList.add('fa-eye')
                  customInput.type='text'
              }else {
                eyeIcon.classList.remove('fa-eye')
                eyeIcon.classList.add('fa-eye-slash')
                customInput.type='password'
      
              }
            })
          }
        })
}

function linkInputsToNext() {
    allinputs = document.querySelectorAll('.custom-input-x')
    allinputs.forEach(input => {
       input.addEventListener('input', (e) => {
        if(Array.from(allinputs).some(input => input.value.length === 0)){
            // document.querySelector('#auth-next').disabled = true
            document.querySelector('.form-submitter').disabled = true
          }else{
            //  document.querySelector('#auth-next').disabled = false
             document.querySelector('.form-submitter').disabled = false

          }
       })
    })
}

function closeModal(){
    let modalBG = document.getElementById("modal-bg")
    modalBG.classList.add("hidden")
    modalBG.innerHTML = ""
}
function closeNotif(element) {
    element.closest('.notif')?.classList.remove('noti-open')
    element.closest('.notif')?.classList.add('noti-close')
}

function toggleDropdown(ele) {
    let dropdown = ele.querySelector('#user-dropdown')
    
    dropdown.classList.toggle('invisible')
    ele.addEventListener('mouseleave', ()=>dropdown.classList.add('invisible'))
    dropdown.addEventListener('mouseleave', ()=>dropdown.classList.add('invisible'))
}

function controlInputLength(ele, counter, maxlength) {
    let length = ele.value.length
    if (length >= maxlength){
        ele.value = ele.value.slice(0, maxlength)

    }  
    formatted_length = ele.value.length
    counter.innerHTML = formatted_length
}

function updateLength(event, maxlength) {
    // check if it has a counter element
    let contentArea = event.target
    let counter = contentArea.parentNode.querySelector('.counter')
    if (!counter) {
        return
    }

    maxlength = parseInt(maxlength)
    controlInputLength(contentArea,counter, maxlength)
}

// Function to resize the textarea based on its content
function resizeTextarea(event) {
    ocnsole.log('resizing')
    event.target.style.minHeight = 'auto'
    event.target.style.minHeight = `${event.target.scrollHeight}px`;
}

function checkSearchLocation(event) {
    // ensure min search lenghth is 3
    // console.log(event.target.value.length, event.target.value)
    if (event.target.value.length == 0){

        input = event.target
        parent = input.closest('.results-wrapper')
        
        // hide clear icon and close map clickers and clear results
        parent.querySelector('.clear-icon').classList.add('invisible')
        document.querySelectorAll('.map-clicker').forEach(clicker => {
            clicker.classList.add('hidden')
            clicker.classList.remove('flex')
        })
        parent.querySelector('.results-container').innerHTML = ''
        return false
    }

    return event.target.value.length > 2
}

function swapImg(img, imgID) {

    let map = {
        // 'dod': 'https://www.uber-assets.com/image/upload/f_auto,q_auto:eco,c_fill,w_1895,h_1001/v1653688465/assets/29/74ec2f-a727-47e1-9695-c78f8dadee5f/original/DotCom_Update_Earner_bg2x.jpg',
        // 'eat':  "https://www.uber-assets.com/image/upload/f_auto,q_auto:eco,c_fill,w_1895,h_899/v1613521576/assets/9d/2ff1e0-a207-425a-a1b8-cf40c95d6567/original/Eats_Home_bg_desktop2x.png",
        // 'ride': 'https://www.uber-assets.com/image/upload/f_auto,q_auto:eco,c_fill,w_1895,h_966/v1653688612/assets/4e/98a67b-fa75-455d-b932-2d3ba478a4ed/original/DotCom_Update_Rider_bg2x.jpg',
    'dod':'/static/assets/bg/man-driver.webp',
    'eat':'/static/assets/bg/lady.webp',
    'ride':'/static/assets/bg/passenger.webp',
    'dashboard':'/static/assets/bg/dashboard.webp',
    'vd':'/static/assets/bg/vd.webp'
    
    }

    let resImg = map[img]
    let imgElmt = document.querySelector(imgID)
    if (resImg && imgElmt) {
        imgElmt.src = resImg
    }
   
}

function closeDrawer() {

    let drawer = document.querySelector('#drawer')
    drawer.classList.remove('!opacity-100')
    drawer.classList.add('opacity-0')
    drawer.classList.remove('!h-screen')
    drawer.classList.add('h-0')
    drawer.dataset.content = ''

    // rotate user button icon
    document.querySelector('#user-button')?.querySelector('svg')?.classList.remove('rotate-180')

    document.body.classList.remove('overflow-hidden')

}
function checkDrawer() {

    let drawState = document.querySelector('#drawer').classList.contains('!opacity-100')
    if (!drawState) {
        document.body.classList.add('overflow-hidden')
    }

   return drawState
}

function checkDrawerContent(givenContent) {
    let drawer = document.querySelector('#drawer')
    
    let drawContent = drawer?.dataset.content

    // rotate user button icon
    let contentIsLoggedIn = givenContent == 'logged-in' 
    document.querySelector('#user-button')?.querySelector('svg')?.classList.toggle('rotate-180', (!checkDrawer() && contentIsLoggedIn) || contentIsLoggedIn)

    if (drawContent == givenContent) {
       closeDrawer()
        drawer.dataset.content = ''
        return false

    }
 
    return true
}

const handleAuthNext = (enabled, form) => {
    let next = document.querySelector('#auth-next')
    
    next.addEventListener('click', (e) => {
       e.preventDefault()
       form.querySelector('.submitter')?.click()
    })
 
    if (enabled) {
       next.classList.remove('disabled')
       next.disabled = false
    } else {
       next.classList.add('disabled')
       next.disabled = true
    }
 }

 function getDValue(selector, property) {
    let element = document.querySelector(selector)
    if (element) {
        return element.dataset[property]
    }
}

  function handleCreditCardInfo(){
    // split every 4 digits with a space and trim the last space, dont allow more than 16 digits
    // dont allow anything other than numbers

    // console.log('handling credit card info')
    let cardNumber = document.querySelector('#card_number')
    if (cardNumber){
        cardNumber.addEventListener('input', (e) => {
            let value = e.target.value
            
            if (e.key != "Backspace" && value.slice(-1).match(/\D/)) {
                e.target.value = value.replace(/[^0-9]/g, '');
                value = e.target.value
            }

            let formatted = value.replace(/\s+/g, '').replace(/(\d{4})/g, '$1 ').trim()

            e.target.value = formatted
            if (formatted.length > 19) {
                e.target.value = formatted.slice(0, 19)
            }
        
        })
    }

    let expiry = document.querySelector('#expiry_date')
    if (expiry) {
        expiry.addEventListener('input', (e) => {
            let value = e.target.value
            if (value.slice(-1).match(/\D/)) {

                if (value.length === 3 && value.slice(-1) == '/'){

                }else{
                    e.target.value = value.replace(/[^0-9]/g, '');
                    value = e.target.value
                }
            }

            if (value.length > 2 && !value.includes('/')){
                value = value.slice(0, 2) + '/' + value.slice(2);
            }
            formatted=value
            e.target.value = formatted
            if (formatted.length > 7) {
                e.target.value = formatted.slice(0, 7)
            }
        
        })
    }

    let cvv = document.querySelector('#cvv')
    if (cvv) {
        cvv.addEventListener('input', (e) => {
            let value = e.target.value
            if (value.slice(-1).match(/\D/)) {
                e.target.value = value.replace(/[^0-9]/g, '');
                value = e.target.value
            }
            let formatted = value.replace(/\s+/g, '').replace(/(\d{3})/g, '$1 ').trim()
            e.target.value = formatted
            if (formatted.length > 3) {
                e.target.value = formatted.slice(0, 3)
            }
        
        })
    }
  }

function updateRide(rideType) {
    // update ride type on request ride button
    let rbuttonText = document.querySelector('#request-ride')?.querySelector('.text')
    if (rbuttonText) {
        result = rbuttonText.innerHTML.split(" ")[0] + " " + rideType
        rbuttonText.innerText = result
    }
}


function restoreBody() {
    document.body.classList.remove('overflow-hidden')
}

function evalRideForm() {

    // check if pickup and dropoff are set
    let rideForm = document.querySelector('#rider-form')
    rideForm.querySelector('.form-submitter').disabled = true
    let pickupMarkerPosition = markers?.pickup?.coords;
    let dropoffMarkerPosition = markers.dropoff?.coords;
    if (pickupMarkerPosition && dropoffMarkerPosition){
        rideForm.querySelector('.form-submitter').disabled = false
    }
}
const initChat = (room, user_id) => {
    // initialises chat 
    const el = document.getElementById('messages')
    el.scrollTop = el.scrollHeight

    var socket = io.connect(window.location.origin +  '/chat');
      socket.on('connect', function() {
         socket.emit('join', {
               room: room
         });
      });

        socket.on('receive message', function(data) {
           document.getElementById('chat-messages').appendChild(htmx.parseHTML(data.msg, 1));
        });

        socket.on('send message', function(data) {
           document.getElementById('chat-messages').appendChild(htmx.parseHTML(data.msg, 1));
        });

        socket.on('leave', function(data) {
           let template = htmx.parseHTML(data.template, 1);
           console.log(template);
           document.querySelector('#page-content').innerHTML = '';
           document.querySelector('#page-content').appendChild(template);
           
           setTimeout(() => {
              window.location.href = data.redirect_url;
           }, 3500);
        });


        // send a chat message through button click or enter key
           let chatInput = document.querySelector('#chat-input');

           const sendMsg = () => {
              
              const msg = chatInput.value?.trim();

              // front end check if msg is empty
              if (!msg || msg === '' || msg.length === 0) {
                 return;
              }
              socket.send({'msg': msg, 'sender':user_id, 'room': room});
              chatInput.value = '';
           }
           document.querySelector('#send').onclick = sendMsg;
           chatInput.addEventListener('keyup', function(event) {
              if (event.keyCode === 13) {
                 event.preventDefault();
                 sendMsg();
              }
           });

        // leave chat room
           document.querySelector('#end').onclick = () => {
              socket.emit('leave', {
               room: room
         });
           };
        
     }