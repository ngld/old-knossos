declare module 'xbbcode' {
	interface Node {
		getAttribute(attr: string): string;
		getContent(): string;
		getOption(): string;
	}

	type Tags = {
		[key: string]: string | ((tag: Node) => string);
	};

	function create(tags: Tags): (source: string) => string;
}
