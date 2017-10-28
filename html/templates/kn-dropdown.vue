<script>
export default {
    props: {
        btn_style: {
            default: 'icon'
        }
    },

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
	<div :class="{ 'dropdown-mod-btn': btn_style === 'options', dropdown: true }">
        <button v-if="btn_style === 'options'" class="mod-btn btn-grey" @click="active = !active">Options</button>
	    <button v-else class="dropbtn" @click="active = !active"></button>
	    <div class="dropdown-content" v-if="active">
	        <slot>No menu items!</slot>
	    </div>
	</div>
</template>