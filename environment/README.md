# environment — exact software versions

One small environment per analysis step, not one mega-environment
(a large solve is slow, fragile, and hides which package a step actually needs).

    env-<step>.yml        conda spec, with versions pinned
    env-<step>.lock.txt   exact resolved versions, captured after creation

Record the environment whenever a package is added. Random seeds live in
`configs/`, not here.
