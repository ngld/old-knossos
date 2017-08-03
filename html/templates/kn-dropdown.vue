<script>
export default {
    data: () => ({
        active: false
    }),

    watch: {
        active(val) {
            if(val) {
                this.$emit('open');

                // The delay is necessary, otherwise it would trigger on the click that opened the dropdown.
                setTimeout(() => window.addEventListener('click', this._closeHandler), 100);
            } else {
                this.$emit('close');

                window.removeEventListener('click', this._closeHandler);
            }

            this.$emit('change', val);
        }
    },

    methods: {
        _closeHandler() {
            this.active = false;
        }
    }
};
</script>
<template>
	<div class="dropdown">
	    <button class="dropbtn" @click="active = !active"></button>
	    <div class="dropdown-content" v-if="active">
	        <slot>No menu items!</slot>
	    </div>
	</div>
</template>