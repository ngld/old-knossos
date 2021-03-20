module.exports = function ({ types: t }) {
  return {
    visitor: {
      ImportDeclaration: {
        enter(path) {
          // Replace grouped imports for @meronex/icons/* into seperate imports to avoid
          // bundling unused icons.
          // This turns the following
          //    import {BsIconA, BsIconB} from '@meronex/icons/bs';
          // into this:
          //    import BsIconA from '@meronex/icons/bs/BsIconA';
          //    import BsIconB from '@meronex/icons/bs/BsIconB';
          const module = path.node.source.value;
          if (module.startsWith('@meronex/icons/')) {
            const collection = module.substring(15);
            if (collection.includes('/')) {
              return;
            }

            const imports = [];
            for (const spec of path.node.specifiers) {
              if (spec.type === 'ImportSpecifier') {
                imports.push(
                  t.importDeclaration(
                    [t.importDefaultSpecifier(spec.imported)],
                    t.stringLiteral(module + '/' + spec.imported.name),
                  ),
                );
              }
            }

            path.replaceWithMultiple(imports);
          }
        },
      },
    },
  };
};
