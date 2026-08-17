/**
 * Makes browser-translate DOM corruption a no-op instead of a crash.
 *
 * `translate="no"` (index.html) only stops *automatic* translation — a user
 * who explicitly turns translation on (confirmed via a screen recording:
 * iOS Control Center showed "Перевод / Английский" engaged) gets it
 * regardless of that hint. Translate then rewrites text nodes in place
 * behind React's back, and the next unrelated re-render tries to
 * removeChild/insertBefore DOM it no longer recognizes, throwing
 * "Failed to execute 'removeChild' on 'Node'" mid-commit — that's what
 * ErrorBoundary.tsx has been recovering from. But if translation is
 * continuously active (not a one-shot pass), every fresh remount gets
 * re-corrupted immediately, so the boundary's wipe-and-retry just loops
 * forever, which is what a permanently stuck black screen actually is.
 *
 * This patches the two DOM methods that throw in exactly that scenario so
 * they check "is this actually still my child / still a real reference
 * point" first, matching a well-known community workaround for this same
 * React-vs-translate incompatibility (facebook/react#11538). No-ops
 * instead of throwing — worst case a translated text node lingers one
 * frame out of sync, instead of the whole app crashing.
 */
export function patchDomForTranslate(): void {
  if (typeof Node !== "function" || !Node.prototype) return;

  const originalRemoveChild = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(this: Node, child: T): T {
    if (child.parentNode !== this) {
      return child;
    }
    return originalRemoveChild.call(this, child) as T;
  };

  const originalInsertBefore = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function <T extends Node>(
    this: Node,
    newNode: T,
    referenceNode: Node | null,
  ): T {
    if (referenceNode && referenceNode.parentNode !== this) {
      return newNode;
    }
    return originalInsertBefore.call(this, newNode, referenceNode) as T;
  };
}
