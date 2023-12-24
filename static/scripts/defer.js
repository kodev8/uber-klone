// htmx backend triggers
document.addEventListener("closeModal",  closeModal)
document.addEventListener('restoreBody', restoreBody)
document.addEventListener('evalRideForm', evalRideForm)
document.addEventListener("linkInputsToNext",  linkInputsToNext)
document.addEventListener("handleCustomInputs", () => { handleCustomInputs(), handleCreditCardInfo()})
document.addEventListener("initChat",  (evt) => {  initChat(evt.detail.room, evt.detail.user_id)})
document.addEventListener("drawRoute",  (evt) => {  drawRoute(evt)})
document.addEventListener("initDatePickers", Flowbite.initDatepickers) // since swapping with htmx, reinitialize datepickers
document.addEventListener("initMap", (evt) => {
    if (!evt.detail.fresh ) return
    initMap()
})
document.addEventListener('setInAuthSessionId', (outerevt) => {
    document.addEventListener('htmx:configRequest', (evt) => {
        evt.detail.headers = {
            ...evt.detail.headers,
            'X-Auth-Session-Id': outerevt.detail.inAuthSessionId
        }
    })
})

window.addEventListener('popstate', function(event) {
// clear messages when going back in history
    document.querySelector('#messages').innerHTML = ''
})



//     htmx.logAll();
//     htmx.on("htmx:afterRequest", function(evt) {
// console.log("The element that dispatched the request: ", evt.detail.elt);
// console.log("The XMLHttpRequest: ", evt.detail.xhr);
// console.log("The target of the request: ", evt.detail.target);
// console.log("The configuration of the AJAX request: ", evt.detail.requestConfig);
// console.log("The event that triggered the request: ", evt.detail.requestConfig.triggeringEvent);
// console.log("True if the response has a 20x status code or is marked detail.isError = false in the htmx:beforeSwap event, else false: ", evt.detail.successful);
// console.log("true if the response does not have a 20x status code or is marked detail.isError = true in the htmx:beforeSwap event, else false: ", evt.detail.failed);
// console.log('BREAKE')
// console.log(' ')

// });


