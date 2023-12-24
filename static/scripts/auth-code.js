function authCodeInit() {

let codeInputs = document.querySelectorAll(".code-input")
let codeForm = document.querySelector('#auth-flow-form') 
codeInputs.forEach((input, index) => {
   input.addEventListener("keydown", (e) => {
      if (e.key == "Backspace" && e.target.value.length == 0) {
         if (index > 0) {
            codeInputs[index - 1].focus();
         }
      }
   })

   input.addEventListener("input", (e) => {

        codeInputs.forEach((input, index) => {input.classList.remove( '!border-red-500')})
        codeForm.querySelector('#code-error')?.classList.add('hidden')

        if ( /^\d$/.test(e.target.value)) {
        
      if (index == 0 && e.target.value.length == 4) {
         let baseval = e.target.value
         e.target.value = baseval.slice(0, 1)
         d2 = document.querySelector('#d2')
         d2.value = baseval.slice(1, 2)
         d3 = document.querySelector('#d3')
         d3.value =baseval.slice(2, 3)
         d4 = document.querySelector('#d4')
         d4.value = baseval.slice(3, 4)
         codeInputs[3].blur()
         setTimeout(() => {

            form.querySelector('button').click()
            
         }, 700);

         handleAuthNext(true, codeForm)
         
      }
      else if (e.target.value.length > 0) {
         var store = e.target.value.slice(0, 1)
         e.target.value = ''
         for(let i = 0; i < codeInputs.length; i++) {
            if (codeInputs[i].value.length == 0) {
               codeInputs[i].value = store
               if (i < 3){
                  codeInputs[i + 1].focus() 
               }
               else {
                codeInputs[3].blur()
                  codeForm.querySelector('button').click()
                  handleAuthNext(true, codeForm)
               }
               break
            }
           
      }}
    }else{
        e.target.value = ''

    }
         
   })
});
    
    }


authCodeInit()