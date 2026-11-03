// Inspect references to a bounded native dispatch table; outputs stay local.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import java.nio.file.*;
import java.util.*;
public class OpenJadeRainTable extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectory(out);
  var functions=new LinkedHashSet<ghidra.program.model.listing.Function>();StringBuilder text=new StringBuilder();
  for(long p=0xa6ea1cL;p<0xa6ea48L;p+=4){var a=toAddr(p);text.append(a+" = "+Integer.toHexString(getInt(a))+"\n");for(var r:getReferencesTo(a)){text.append(r+"\n");var f=getFunctionContaining(r.getFromAddress());if(f!=null)functions.add(f);}}
  for(long p:new long[]{0x7a9018L,0x7a9014L,0x7a9000L,0x7a8fdcL,0x7a5934L})text.append(String.format("constant %08x %08x %.12g\n",p,getInt(toAddr(p)),Float.intBitsToFloat(getInt(toAddr(p)))));
  for(long p:new long[]{0x42ee80L,0x4307f0L,0x42d6d0L,0x41b180L}){var f=getFunctionAt(toAddr(p));if(f==null){disassemble(toAddr(p));f=createFunction(toAddr(p),null);}if(f!=null){StringBuilder asm=new StringBuilder();var it=currentProgram.getListing().getInstructions(f.getBody(),true);while(it.hasNext()){var i=it.next();asm.append(i.getAddress()+" "+i+"\n");}Files.writeString(out.resolve(Long.toHexString(p)+".asm"),asm.toString());}}
  Files.writeString(out.resolve("table.txt"),text.toString());var dec=new DecompInterface();dec.openProgram(currentProgram);
  try{for(var f:functions){var r=dec.decompileFunction(f,60,monitor);if(r.decompileCompleted())Files.writeString(out.resolve(f.getEntryPoint()+".c"),r.getDecompiledFunction().getC());}}finally{dec.dispose();}
 }
}


