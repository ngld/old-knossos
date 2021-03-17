type MessageReceiver = (msg: ArrayBuffer) => void;
declare function knShowDevTools();
declare function knAddMessageListener(cb: MessageReceiver);
declare function knRemoveMessageListener(cb: MessageReceiver);
declare function knOpenFile(title: string, default_filename: string, accepted: string[]): Promise<string>;
declare function knOpenFolder(title: string, default_folder: string): Promise<string>;
declare function knSaveFile(title: string, default_filename: string, accepted: string[]): Promise<string>;
